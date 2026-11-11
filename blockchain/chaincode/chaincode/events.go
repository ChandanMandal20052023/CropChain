package chaincode

import (
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// createEvent records an immutable append-only event for a batch and emits a Fabric chaincode event.
func createEvent(ctx contractapi.TransactionContextInterface, batch *Batch, eventType string, actor *CallerIdentity, dataStr string) (*BatchEvent, error) {
	if batch == nil || batch.BatchID == "" {
		return nil, fmt.Errorf("cannot create event for nil batch or empty batchId")
	}

	eventSeq := len(batch.Events) + 1
	eventID := fmt.Sprintf("EVENT_%s_%03d", batch.BatchID, eventSeq)

	timestamp, err := getTxTimestamp(ctx)
	if err != nil {
		return nil, err
	}

	actorID := "SYSTEM"
	actorRole := "SYSTEM"
	orgMSP := "SYSTEM"
	if actor != nil {
		actorID = actor.ActorID
		actorRole = actor.Role
		orgMSP = actor.MSP
	}

	event := &BatchEvent{
		EventID:   eventID,
		BatchID:   batch.BatchID,
		EventType: eventType,
		ActorID:   actorID,
		ActorRole: actorRole,
		OrgMSP:    orgMSP,
		Data:      dataStr,
		Timestamp: timestamp,
	}

	eventBytes, err := json.Marshal(event)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal batch event %s: %w", eventID, err)
	}

	// Persist event under predictable immutable key: EVENT_<batchId>_<sequence>
	if err := ctx.GetStub().PutState(eventID, eventBytes); err != nil {
		return nil, fmt.Errorf("failed to write batch event %s to ledger: %w", eventID, err)
	}

	// Append event reference to batch's event list
	batch.Events = append(batch.Events, eventID)

	// Emit Fabric chaincode event for the Django event listener / off-chain projections
	if err := ctx.GetStub().SetEvent(eventType, eventBytes); err != nil {
		return nil, fmt.Errorf("failed to emit chaincode event %s: %w", eventType, err)
	}

	return event, nil
}

// getEvent retrieves a single BatchEvent from world state.
func getEvent(ctx contractapi.TransactionContextInterface, eventID string) (*BatchEvent, error) {
	if eventID == "" {
		return nil, fmt.Errorf("eventId cannot be empty")
	}

	data, err := ctx.GetStub().GetState(eventID)
	if err != nil {
		return nil, fmt.Errorf("failed to read event %s: %w", eventID, err)
	}
	if data == nil || len(data) == 0 {
		return nil, fmt.Errorf("event '%s' not found", eventID)
	}

	var event BatchEvent
	if err := json.Unmarshal(data, &event); err != nil {
		return nil, fmt.Errorf("failed to unmarshal event %s: %w", eventID, err)
	}

	return &event, nil
}

// getBatchEvents retrieves all historical events associated with a batch in chronological order.
func getBatchEvents(ctx contractapi.TransactionContextInterface, batchID string) ([]*BatchEvent, error) {
	batch, err := getBatch(ctx, batchID)
	if err != nil {
		return nil, err
	}

	var events []*BatchEvent
	for _, eventID := range batch.Events {
		event, err := getEvent(ctx, eventID)
		if err != nil {
			return nil, fmt.Errorf("failed to retrieve event %s for batch %s: %w", eventID, batchID, err)
		}
		events = append(events, event)
	}

	return events, nil
}
