package chaincode

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// checkIdempotency checks if a transaction with the given txKey was already processed.
// If found, returns (cachedResult, true, nil). Otherwise returns ("", false, nil).
func checkIdempotency(ctx contractapi.TransactionContextInterface, txKey string) (string, bool, error) {
	if txKey == "" {
		return "", false, nil
	}

	key := fmt.Sprintf("IDEMP_%s", txKey)
	data, err := ctx.GetStub().GetState(key)
	if err != nil {
		return "", false, fmt.Errorf("failed to query idempotency key %s: %w", key, err)
	}

	if data == nil || len(data) == 0 {
		return "", false, nil
	}

	var record IdempotencyRecord
	if err := json.Unmarshal(data, &record); err != nil {
		return string(data), true, nil
	}

	return record.Result, true, nil
}

// storeIdempotencyResult records the output of a successfully executed transaction key.
func storeIdempotencyResult(ctx contractapi.TransactionContextInterface, txKey string, result interface{}) error {
	if txKey == "" {
		return nil
	}

	var resultStr string
	switch v := result.(type) {
	case string:
		resultStr = v
	case []byte:
		resultStr = string(v)
	default:
		bytes, err := json.Marshal(v)
		if err != nil {
			return fmt.Errorf("failed to marshal idempotency result: %w", err)
		}
		resultStr = string(bytes)
	}

	record := IdempotencyRecord{
		TxKey:     txKey,
		Result:    resultStr,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}

	data, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal idempotency record: %w", err)
	}

	key := fmt.Sprintf("IDEMP_%s", txKey)
	if err := ctx.GetStub().PutState(key, data); err != nil {
		return fmt.Errorf("failed to persist idempotency key %s: %w", key, err)
	}

	return nil
}
