package chaincode

import (
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// queryBatchesWithSelector executes a CouchDB rich query string.
func queryBatchesWithSelector(ctx contractapi.TransactionContextInterface, queryString string) ([]*Batch, error) {
	resultsIterator, err := ctx.GetStub().GetQueryResult(queryString)
	if err != nil {
		return nil, fmt.Errorf("failed executing CouchDB query: %w", err)
	}
	defer resultsIterator.Close()

	var batches []*Batch
	for resultsIterator.HasNext() {
		queryResponse, err := resultsIterator.Next()
		if err != nil {
			return nil, fmt.Errorf("error reading query response: %w", err)
		}

		var batch Batch
		if err := json.Unmarshal(queryResponse.Value, &batch); err == nil && batch.BatchID != "" {
			batches = append(batches, &batch)
		}
	}

	return batches, nil
}

// GetBatchesByOwner retrieves batches currently owned by an actor or MSP.
func (c *AgroVaaniContract) GetBatchesByOwner(ctx contractapi.TransactionContextInterface, owner string) ([]*Batch, error) {
	queryString := fmt.Sprintf(`{"selector":{"currentOwner":"%s"}}`, owner)
	return queryBatchesWithSelector(ctx, queryString)
}

// GetBatchesByStage retrieves batches at a specific supply-chain stage.
func (c *AgroVaaniContract) GetBatchesByStage(ctx contractapi.TransactionContextInterface, stage string) ([]*Batch, error) {
	queryString := fmt.Sprintf(`{"selector":{"stage":"%s"}}`, stage)
	return queryBatchesWithSelector(ctx, queryString)
}

// GetBatchesByStatus retrieves batches in a specific lifecycle status.
func (c *AgroVaaniContract) GetBatchesByStatus(ctx contractapi.TransactionContextInterface, status string) ([]*Batch, error) {
	queryString := fmt.Sprintf(`{"selector":{"status":"%s"}}`, status)
	return queryBatchesWithSelector(ctx, queryString)
}

// GetBatchChildren retrieves the direct child batch objects for a given batch.
func (c *AgroVaaniContract) GetBatchChildren(ctx contractapi.TransactionContextInterface, batchID string) ([]*Batch, error) {
	batch, err := getBatch(ctx, batchID)
	if err != nil {
		return nil, err
	}

	var children []*Batch
	for _, childID := range batch.ChildBatchIDs {
		child, err := getBatch(ctx, childID)
		if err == nil {
			children = append(children, child)
		}
	}

	return children, nil
}

// GetBatchParents retrieves the direct parent batch objects for a given batch.
func (c *AgroVaaniContract) GetBatchParents(ctx contractapi.TransactionContextInterface, batchID string) ([]*Batch, error) {
	batch, err := getBatch(ctx, batchID)
	if err != nil {
		return nil, err
	}

	var parents []*Batch
	for _, parentID := range batch.ParentBatchIDs {
		parent, err := getBatch(ctx, parentID)
		if err == nil {
			parents = append(parents, parent)
		}
	}

	return parents, nil
}
