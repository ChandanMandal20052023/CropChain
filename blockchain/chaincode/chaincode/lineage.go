package chaincode

import (
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// createLineageEdge writes a directed DAG edge from parent batch to child batch in world state.
func createLineageEdge(ctx contractapi.TransactionContextInterface, fromBatchID, toBatchID, action, actorID string) (*LineageEdge, error) {
	if fromBatchID == "" || toBatchID == "" {
		return nil, fmt.Errorf("fromBatchId and toBatchId cannot be empty for lineage edge")
	}

	timestamp, err := getTxTimestamp(ctx)
	if err != nil {
		return nil, err
	}

	edge := &LineageEdge{
		FromBatchID: fromBatchID,
		ToBatchID:   toBatchID,
		Action:      action,
		ActorID:     actorID,
		Timestamp:   timestamp,
	}

	edgeBytes, err := json.Marshal(edge)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal lineage edge: %w", err)
	}

	edgeKey := fmt.Sprintf("EDGE_%s_%s", fromBatchID, toBatchID)
	if err := ctx.GetStub().PutState(edgeKey, edgeBytes); err != nil {
		return nil, fmt.Errorf("failed to write lineage edge %s: %w", edgeKey, err)
	}

	// Update incoming edges index for toBatchID
	inKey := fmt.Sprintf("IN_EDGES_%s", toBatchID)
	var inEdges []LineageEdge
	inData, err := ctx.GetStub().GetState(inKey)
	if err == nil && len(inData) > 0 {
		_ = json.Unmarshal(inData, &inEdges)
	}
	inEdges = append(inEdges, *edge)
	inData, _ = json.Marshal(inEdges)
	_ = ctx.GetStub().PutState(inKey, inData)

	// Update outgoing edges index for fromBatchID
	outKey := fmt.Sprintf("OUT_EDGES_%s", fromBatchID)
	var outEdges []LineageEdge
	outData, err := ctx.GetStub().GetState(outKey)
	if err == nil && len(outData) > 0 {
		_ = json.Unmarshal(outData, &outEdges)
	}
	outEdges = append(outEdges, *edge)
	outData, _ = json.Marshal(outEdges)
	_ = ctx.GetStub().PutState(outKey, outData)

	return edge, nil
}

// getIncomingEdges retrieves all direct parent edges for a batch.
func getIncomingEdges(ctx contractapi.TransactionContextInterface, batchID string) ([]LineageEdge, error) {
	inKey := fmt.Sprintf("IN_EDGES_%s", batchID)
	data, err := ctx.GetStub().GetState(inKey)
	if err != nil {
		return nil, err
	}
	if len(data) == 0 {
		return []LineageEdge{}, nil
	}

	var edges []LineageEdge
	if err := json.Unmarshal(data, &edges); err != nil {
		return nil, err
	}
	return edges, nil
}

// getBatchLineage executes an iterative backward DAG traversal to reconstruct complete provenance.
// Returns target batch, all ancestor batches, edges, events, and issued certificates.
func getBatchLineage(ctx contractapi.TransactionContextInterface, rootBatchID string) (*LineageProvenance, error) {
	targetBatch, err := getBatch(ctx, rootBatchID)
	if err != nil {
		return nil, fmt.Errorf("target batch %s not found: %w", rootBatchID, err)
	}

	visitedBatches := make(map[string]bool)
	queue := []string{rootBatchID}

	var allBatches []*Batch
	var allEdges []LineageEdge
	var allEvents []*BatchEvent
	var allCertificates []*Certificate

	for len(queue) > 0 {
		currID := queue[0]
		queue = queue[1:]

		if visitedBatches[currID] {
			continue
		}
		visitedBatches[currID] = true

		currBatch, err := getBatch(ctx, currID)
		if err != nil {
			continue
		}
		allBatches = append(allBatches, currBatch)

		// Collect events for current batch
		events, err := getBatchEvents(ctx, currID)
		if err == nil {
			allEvents = append(allEvents, events...)
		}

		// Collect certificates bound to current batch
		certs, err := getCertificatesForBatch(ctx, currID)
		if err == nil {
			allCertificates = append(allCertificates, certs...)
		}

		// Traverse parents via ParentBatchIDs & incoming edges
		for _, parentID := range currBatch.ParentBatchIDs {
			if !visitedBatches[parentID] {
				queue = append(queue, parentID)
			}
		}

		inEdges, err := getIncomingEdges(ctx, currID)
		if err == nil {
			for _, edge := range inEdges {
				allEdges = append(allEdges, edge)
				if !visitedBatches[edge.FromBatchID] {
					queue = append(queue, edge.FromBatchID)
				}
			}
		}
	}

	return &LineageProvenance{
		TargetBatch:  targetBatch,
		AllBatches:   allBatches,
		Edges:        allEdges,
		Events:       allEvents,
		Certificates: allCertificates,
	}, nil
}
