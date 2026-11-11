package chaincode

import (
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// getTxTimestamp retrieves a deterministic RFC3339 timestamp from the transaction context.
func getTxTimestamp(ctx contractapi.TransactionContextInterface) (string, error) {
	txTime, err := ctx.GetStub().GetTxTimestamp()
	if err != nil || txTime == nil {
		return time.Now().UTC().Format(time.RFC3339), nil
	}
	return time.Unix(txTime.Seconds, int64(txTime.Nanos)).UTC().Format(time.RFC3339), nil
}

// generateBatchID generates a globally unique, atomic Batch ID formatted as <Prefix>-<YYYY>-<SeqNumber>.
// Uses on-chain sequence counters: SEQCTR_RAW, SEQCTR_CC, SEQCTR_WH, SEQCTR_MFG, SEQCTR_RET.
func generateBatchID(ctx contractapi.TransactionContextInterface, prefix string) (string, error) {
	var seqKey string
	switch prefix {
	case PrefixRAW:
		seqKey = SeqCtrRAW
	case PrefixCC:
		seqKey = SeqCtrCC
	case PrefixWH:
		seqKey = SeqCtrWH
	case PrefixMFG:
		seqKey = SeqCtrMFG
	case PrefixRET:
		seqKey = SeqCtrRET
	default:
		return "", fmt.Errorf("unsupported batch prefix '%s'; valid prefixes are RAW, CC, WH, MFG, RET", prefix)
	}

	counterBytes, err := ctx.GetStub().GetState(seqKey)
	if err != nil {
		return "", fmt.Errorf("failed to read sequence counter %s: %w", seqKey, err)
	}

	currentSeq := 0
	if len(counterBytes) > 0 {
		currentSeq, err = strconv.Atoi(string(counterBytes))
		if err != nil {
			return "", fmt.Errorf("corrupted sequence counter for %s: %w", seqKey, err)
		}
	}

	nextSeq := currentSeq + 1
	if err := ctx.GetStub().PutState(seqKey, []byte(strconv.Itoa(nextSeq))); err != nil {
		return "", fmt.Errorf("failed to update sequence counter %s: %w", seqKey, err)
	}

	txTimeStr, _ := getTxTimestamp(ctx)
	year := "2026"
	if parsedTime, err := time.Parse(time.RFC3339, txTimeStr); err == nil {
		year = fmt.Sprintf("%04d", parsedTime.Year())
	}

	batchID := fmt.Sprintf("%s-%s-%06d", prefix, year, nextSeq)
	return batchID, nil
}

// getBatch retrieves a Batch from world state by its Batch ID.
func getBatch(ctx contractapi.TransactionContextInterface, batchID string) (*Batch, error) {
	if batchID == "" {
		return nil, fmt.Errorf("batchId cannot be empty")
	}

	key := fmt.Sprintf("BATCH_%s", batchID)
	data, err := ctx.GetStub().GetState(key)
	if err != nil {
		return nil, fmt.Errorf("failed to read batch %s from world state: %w", batchID, err)
	}

	if data == nil || len(data) == 0 {
		return nil, fmt.Errorf("batch with ID '%s' does not exist", batchID)
	}

	var batch Batch
	if err := json.Unmarshal(data, &batch); err != nil {
		return nil, fmt.Errorf("failed to deserialize batch data for %s: %w", batchID, err)
	}

	return &batch, nil
}

// putBatch persists a Batch into world state.
func putBatch(ctx contractapi.TransactionContextInterface, batch *Batch) error {
	if batch == nil || batch.BatchID == "" {
		return fmt.Errorf("cannot persist nil batch or empty batchId")
	}

	data, err := json.Marshal(batch)
	if err != nil {
		return fmt.Errorf("failed to marshal batch %s: %w", batch.BatchID, err)
	}

	key := fmt.Sprintf("BATCH_%s", batch.BatchID)
	if err := ctx.GetStub().PutState(key, data); err != nil {
		return fmt.Errorf("failed to write batch %s to world state: %w", batch.BatchID, err)
	}

	return nil
}

// validateStateTransition enforces valid sequential lifecycle states.
func validateStateTransition(currentStatus, nextStatus string) error {
	if currentStatus == nextStatus {
		return nil
	}

	validTransitions := map[string][]string{
		StatusPending:        {StatusQualityChecked, StatusAccepted, StatusRejected},
		StatusQualityChecked: {StatusAccepted, StatusRejected, StatusQualityChecked},
		StatusAccepted:       {StatusPacked, StatusInTransit, StatusInWarehouse},
		StatusRejected:       {}, // Terminal state
		StatusPacked:         {StatusInTransit, StatusInWarehouse},
		StatusInTransit:      {StatusInWarehouse, StatusManufactured, StatusAtRetail},
		StatusInWarehouse:    {StatusInTransit, StatusManufactured, StatusConsumed},
		StatusManufactured:   {StatusAtRetail, StatusInTransit, StatusConsumed},
		StatusAtRetail:       {StatusSold, StatusConsumed},
		StatusConsumed:       {}, // Terminal state
		StatusSold:           {}, // Terminal state
	}

	allowed, exists := validTransitions[currentStatus]
	if !exists {
		return fmt.Errorf("invalid current status '%s'", currentStatus)
	}

	for _, s := range allowed {
		if s == nextStatus {
			return nil
		}
	}

	return fmt.Errorf("illegal state transition from '%s' to '%s'", currentStatus, nextStatus)
}
