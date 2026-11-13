package chaincode

import (
	"encoding/json"
	"fmt"
	"math"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// AgroVaaniContract implements the authoritative Hyperledger Fabric smart contract for the supply chain.
type AgroVaaniContract struct {
	contractapi.Contract
}

// ==========================================
// 1. Farmer — CreateBatch
// ==========================================

// CreateBatch allows authorized farmers to register a new raw harvest batch (RAW-YYYY-XXXXXX).
func (c *AgroVaaniContract) CreateBatch(ctx contractapi.TransactionContextInterface, inputJSON string) (*Batch, error) {
	caller, err := requireRole(ctx, RoleFarmer)
	if err != nil {
		return nil, err
	}

	var input CreateBatchInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid create batch payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	if input.Quantity <= 0 {
		return nil, fmt.Errorf("batch quantity must be strictly positive (got %.2f)", input.Quantity)
	}
	if input.CropType == "" {
		return nil, fmt.Errorf("cropType cannot be empty")
	}
// batch id generation code 
	batchID, err := generateBatchID(ctx, PrefixRAW)
	if err != nil {
		return nil, fmt.Errorf("failed to generate raw batch ID: %w", err)
	}

	txTime, err := getTxTimestamp(ctx)
	if err != nil {
		return nil, err
	}

	farmerID := input.FarmerID
	if farmerID == "" {
		farmerID = caller.ActorID
	}

	batch := &Batch{
		BatchID:        batchID,
		BatchType:      PrefixRAW,
		CropType:       input.CropType,
		Quantity:       input.Quantity,
		Unit:           input.Unit,
		Stage:          StageFarm,
		Status:         StatusPending,
		CurrentOwner:   farmerID,
		ParentBatchIDs: []string{},
		ChildBatchIDs:  []string{},
		ProcessingLoss: 0,
		Events:         []string{},
		CreatedAt:      txTime,
		UpdatedAt:      txTime,
	}

	eventDataBytes, _ := json.Marshal(map[string]interface{}{
		"farmId":        input.FarmID,
		"farmerId":      farmerID,
		"harvestDate":   input.HarvestDate,
		"landInfo":      input.LandInfo,
		"certification": input.Certification,
		"cropDetails":   input.CropDetails,
	})

	if _, err := createEvent(ctx, batch, EventBatchCreated, caller, string(eventDataBytes)); err != nil {
		return nil, fmt.Errorf("failed to record BATCH_CREATED event: %w", err)
	}

	if err := putBatch(ctx, batch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, batch)
	return batch, nil
}

// ==========================================
// 2. Collection Center — Verify, Accept, Reject, Pack
// ==========================================

// VerifyBatch records quality inspection parameters and creates an immutable QUALITY_CHECK event.
func (c *AgroVaaniContract) VerifyBatch(ctx contractapi.TransactionContextInterface, inputJSON string) (*Batch, error) {
	caller, err := requireRole(ctx, RoleCollectionCenter, RoleInspector)
	if err != nil {
		return nil, err
	}

	var input VerifyBatchInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid verify batch payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	batch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	if err := validateStateTransition(batch.Status, StatusQualityChecked); err != nil {
		return nil, err
	}

	txTime, _ := getTxTimestamp(ctx)
	batch.Status = StatusQualityChecked
	batch.UpdatedAt = txTime

	eventDataBytes, _ := json.Marshal(map[string]interface{}{
		"actualQuantity":   input.ActualQuantity,
		"moistureContent":  input.MoistureContent,
		"qualityGrade":     input.QualityGrade,
		"foreignMaterial":  input.ForeignMaterial,
		"inspectionResult": input.InspectionResult,
		"notes":            input.Notes,
	})

	if _, err := createEvent(ctx, batch, EventQualityCheck, caller, string(eventDataBytes)); err != nil {
		return nil, fmt.Errorf("failed to record QUALITY_CHECK event: %w", err)
	}

	if err := putBatch(ctx, batch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, batch)
	return batch, nil
}

// AcceptBatch marks a verified batch as accepted by the collection center.
func (c *AgroVaaniContract) AcceptBatch(ctx contractapi.TransactionContextInterface, inputJSON string) (*Batch, error) {
	caller, err := requireRole(ctx, RoleCollectionCenter)
	if err != nil {
		return nil, err
	}

	var input AcceptBatchInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid accept batch payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	batch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	if err := validateStateTransition(batch.Status, StatusAccepted); err != nil {
		return nil, err
	}

	txTime, _ := getTxTimestamp(ctx)
	batch.Status = StatusAccepted
	batch.Stage = StageCollectionCenter
	batch.CurrentOwner = caller.ActorID
	batch.UpdatedAt = txTime

	eventDataBytes, _ := json.Marshal(map[string]string{"notes": input.Notes})
	if _, err := createEvent(ctx, batch, EventAccepted, caller, string(eventDataBytes)); err != nil {
		return nil, fmt.Errorf("failed to record ACCEPTED event: %w", err)
	}

	if err := putBatch(ctx, batch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, batch)
	return batch, nil
}

// RejectBatch marks a batch as rejected due to quality failure.
func (c *AgroVaaniContract) RejectBatch(ctx contractapi.TransactionContextInterface, inputJSON string) (*Batch, error) {
	caller, err := requireRole(ctx, RoleCollectionCenter, RoleInspector)
	if err != nil {
		return nil, err
	}

	var input RejectBatchInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid reject batch payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	batch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	if err := validateStateTransition(batch.Status, StatusRejected); err != nil {
		return nil, err
	}

	txTime, _ := getTxTimestamp(ctx)
	batch.Status = StatusRejected
	batch.UpdatedAt = txTime

	eventDataBytes, _ := json.Marshal(map[string]string{"reason": input.Reason})
	if _, err := createEvent(ctx, batch, EventRejected, caller, string(eventDataBytes)); err != nil {
		return nil, fmt.Errorf("failed to record REJECTED event: %w", err)
	}

	if err := putBatch(ctx, batch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, batch)
	return batch, nil
}

// PackBatch packages an accepted RAW batch into a CC-YYYY-XXXXXX collection center batch.
func (c *AgroVaaniContract) PackBatch(ctx contractapi.TransactionContextInterface, inputJSON string) (*Batch, error) {
	caller, err := requireRole(ctx, RoleCollectionCenter)
	if err != nil {
		return nil, err
	}

	var input PackBatchInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid pack batch payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	parentBatch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	if parentBatch.Status != StatusAccepted {
		return nil, fmt.Errorf("cannot pack batch %s in status '%s'; must be ACCEPTED", parentBatch.BatchID, parentBatch.Status)
	}

	childBatchID, err := generateBatchID(ctx, PrefixCC)
	if err != nil {
		return nil, err
	}

	txTime, _ := getTxTimestamp(ctx)
	qty := input.Quantity
	if qty <= 0 {
		qty = parentBatch.Quantity
	}
	unit := input.Unit
	if unit == "" {
		unit = parentBatch.Unit
	}

	childBatch := &Batch{
		BatchID:        childBatchID,
		BatchType:      PrefixCC,
		CropType:       parentBatch.CropType,
		Quantity:       qty,
		Unit:           unit,
		Stage:          StageCollectionCenter,
		Status:         StatusPacked,
		CurrentOwner:   caller.ActorID,
		ParentBatchIDs: []string{parentBatch.BatchID},
		ChildBatchIDs:  []string{},
		ProcessingLoss: 0,
		Events:         []string{},
		CreatedAt:      txTime,
		UpdatedAt:      txTime,
	}

	// Update parent batch
	parentBatch.Status = StatusPacked
	parentBatch.ChildBatchIDs = append(parentBatch.ChildBatchIDs, childBatchID)
	parentBatch.UpdatedAt = txTime

	// Append events and DAG edge
	eventDataBytes, _ := json.Marshal(map[string]interface{}{
		"packageType":   input.PackageType,
		"parentBatchId": parentBatch.BatchID,
		"notes":         input.Notes,
	})
	if _, err := createEvent(ctx, childBatch, EventPacked, caller, string(eventDataBytes)); err != nil {
		return nil, err
	}

	if _, err := createLineageEdge(ctx, parentBatch.BatchID, childBatchID, LineageActionPacked, caller.ActorID); err != nil {
		return nil, err
	}

	if err := putBatch(ctx, parentBatch); err != nil {
		return nil, err
	}
	if err := putBatch(ctx, childBatch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, childBatch)
	return childBatch, nil
}

// ==========================================
// 3. Transporter — TransferBatch
// ==========================================

// TransferBatch updates custody and records transportation details.
func (c *AgroVaaniContract) TransferBatch(ctx contractapi.TransactionContextInterface, inputJSON string) (*Batch, error) {
	caller, err := requireRole(ctx, RoleTransporter, RoleCollectionCenter, RoleManufacturer, RoleWarehouse)
	if err != nil {
		return nil, err
	}

	var input TransferBatchInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid transfer batch payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	batch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	if batch.Status == StatusConsumed || batch.Status == StatusRejected || batch.Status == StatusSold {
		return nil, fmt.Errorf("batch %s is in terminal state '%s' and cannot be transferred", batch.BatchID, batch.Status)
	}

	txTime, _ := getTxTimestamp(ctx)
	batch.Status = StatusInTransit
	batch.Stage = StageTransport
	batch.CurrentOwner = input.ToActorID
	batch.UpdatedAt = txTime

	eventDataBytes, _ := json.Marshal(map[string]string{
		"fromActorId":   caller.ActorID,
		"toActorId":     input.ToActorID,
		"toOrgMsp":      input.ToOrgMSP,
		"vehicleNumber": input.VehicleNumber,
		"routeDetails":  input.RouteDetails,
	})

	if _, err := createEvent(ctx, batch, EventTransferred, caller, string(eventDataBytes)); err != nil {
		return nil, err
	}

	if err := putBatch(ctx, batch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, batch)
	return batch, nil
}

// ==========================================
// 4. Warehouse — StoreBatch
// ==========================================

// StoreBatch receives and verifies incoming batches, generating a WH-YYYY-XXXXXX warehouse batch.
func (c *AgroVaaniContract) StoreBatch(ctx contractapi.TransactionContextInterface, inputJSON string) (*Batch, error) {
	caller, err := requireRole(ctx, RoleWarehouse)
	if err != nil {
		return nil, err
	}

	var input StoreBatchInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid store batch payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	parentBatch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	if parentBatch.Status == StatusConsumed || parentBatch.Status == StatusRejected {
		return nil, fmt.Errorf("cannot store batch %s in status '%s'", parentBatch.BatchID, parentBatch.Status)
	}

	childBatchID, err := generateBatchID(ctx, PrefixWH)
	if err != nil {
		return nil, err
	}

	txTime, _ := getTxTimestamp(ctx)
	qty := input.VerifiedWeight
	if qty <= 0 {
		qty = parentBatch.Quantity
	}

	childBatch := &Batch{
		BatchID:        childBatchID,
		BatchType:      PrefixWH,
		CropType:       parentBatch.CropType,
		Quantity:       qty,
		Unit:           parentBatch.Unit,
		Stage:          StageWarehouse,
		Status:         StatusInWarehouse,
		CurrentOwner:   caller.ActorID,
		ParentBatchIDs: []string{parentBatch.BatchID},
		ChildBatchIDs:  []string{},
		ProcessingLoss: 0,
		Events:         []string{},
		CreatedAt:      txTime,
		UpdatedAt:      txTime,
	}

	parentBatch.Status = StatusInWarehouse
	parentBatch.ChildBatchIDs = append(parentBatch.ChildBatchIDs, childBatchID)
	parentBatch.UpdatedAt = txTime

	eventDataBytes, _ := json.Marshal(map[string]interface{}{
		"warehouseId":    input.WarehouseID,
		"storageSection": input.StorageSection,
		"verifiedWeight": input.VerifiedWeight,
		"condition":      input.Condition,
		"parentBatchId":  parentBatch.BatchID,
	})

	if _, err := createEvent(ctx, childBatch, EventReceivedAtWarehouse, caller, string(eventDataBytes)); err != nil {
		return nil, err
	}

	if _, err := createLineageEdge(ctx, parentBatch.BatchID, childBatchID, LineageActionStored, caller.ActorID); err != nil {
		return nil, err
	}

	if err := putBatch(ctx, parentBatch); err != nil {
		return nil, err
	}
	if err := putBatch(ctx, childBatch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, childBatch)
	return childBatch, nil
}

// ==========================================
// 5. Manufacturer — ProcessBatch (Atomic Multi-Input Multi-Output & Conservation)
// ==========================================

// ProcessBatch atomically converts multiple input batches into multiple output batches (MFG-YYYY-XXXXXX)
// while strictly enforcing the quantity conservation law: sum(inputs) == sum(outputs) + processingLoss.
func (c *AgroVaaniContract) ProcessBatch(ctx contractapi.TransactionContextInterface, inputJSON string) ([]*Batch, error) {
	caller, err := requireRole(ctx, RoleManufacturer)
	if err != nil {
		return nil, err
	}

	var input ProcessBatchInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid process batch payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing []*Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return existing, nil
	}

	if len(input.InputBatchIDs) == 0 {
		return nil, fmt.Errorf("inputBatchIds cannot be empty")
	}
	if len(input.Outputs) == 0 {
		return nil, fmt.Errorf("outputs specification cannot be empty")
	}
	if input.ProcessingLoss < 0 {
		return nil, fmt.Errorf("processingLoss cannot be negative (got %.2f)", input.ProcessingLoss)
	}

	// 1. Read and validate all input batches
	var inputBatches []*Batch
	var totalInputQuantity float64

	for _, inID := range input.InputBatchIDs {
		inBatch, err := getBatch(ctx, inID)
		if err != nil {
			return nil, fmt.Errorf("input batch validation failed: %w", err)
		}
		if inBatch.Status == StatusConsumed {
			return nil, fmt.Errorf("input batch %s is already CONSUMED and cannot be processed again", inID)
		}
		if inBatch.Quantity <= 0 {
			return nil, fmt.Errorf("input batch %s has invalid quantity %.2f", inID, inBatch.Quantity)
		}

		totalInputQuantity += inBatch.Quantity
		inputBatches = append(inputBatches, inBatch)
	}

	// 2. Validate total output quantities
	var totalOutputQuantity float64
	for i, out := range input.Outputs {
		if out.Quantity <= 0 {
			return nil, fmt.Errorf("output batch at index %d has invalid non-positive quantity %.2f", i, out.Quantity)
		}
		totalOutputQuantity += out.Quantity
	}

	// 3. Enforce Strict Quantity Conservation: sum(input) == sum(output) + processingLoss
	expectedSum := totalOutputQuantity + input.ProcessingLoss
	if math.Abs(totalInputQuantity-expectedSum) > 1e-4 {
		return nil, fmt.Errorf("quantity conservation failed: sum(inputs)=%.4f does not equal sum(outputs)=%.4f + loss=%.4f (difference: %.4f)",
			totalInputQuantity, totalOutputQuantity, input.ProcessingLoss, totalInputQuantity-expectedSum)
	}

	txTime, _ := getTxTimestamp(ctx)

	// 4. Generate Output Batches
	var outputBatches []*Batch
	var outputBatchIDs []string

	for _, outSpec := range input.Outputs {
		outBatchID, err := generateBatchID(ctx, PrefixMFG)
		if err != nil {
			return nil, fmt.Errorf("failed to generate MFG batch ID: %w", err)
		}

		cropType := outSpec.ProductType
		if cropType == "" && len(inputBatches) > 0 {
			cropType = inputBatches[0].CropType
		}

		outBatch := &Batch{
			BatchID:        outBatchID,
			BatchType:      PrefixMFG,
			CropType:       cropType,
			Quantity:       outSpec.Quantity,
			Unit:           outSpec.Unit,
			Stage:          StageManufacturing,
			Status:         StatusManufactured,
			CurrentOwner:   caller.ActorID,
			ParentBatchIDs: append([]string(nil), input.InputBatchIDs...),
			ChildBatchIDs:  []string{},
			ProcessingLoss: input.ProcessingLoss,
			Events:         []string{},
			CreatedAt:      txTime,
			UpdatedAt:      txTime,
		}

		outputBatches = append(outputBatches, outBatch)
		outputBatchIDs = append(outputBatchIDs, outBatchID)
	}

	// 5. Atomically update all input batches to CONSUMED and record child IDs
	for _, inBatch := range inputBatches {
		inBatch.Status = StatusConsumed
		inBatch.ChildBatchIDs = append(inBatch.ChildBatchIDs, outputBatchIDs...)
		inBatch.UpdatedAt = txTime

		eventData, _ := json.Marshal(map[string]interface{}{
			"action":          "INPUT_CONSUMED",
			"outputBatchIds":  outputBatchIDs,
			"processingLoss":  input.ProcessingLoss,
			"processDetails":  input.ProcessDetails,
		})
		if _, err := createEvent(ctx, inBatch, EventProcessed, caller, string(eventData)); err != nil {
			return nil, err
		}

		if err := putBatch(ctx, inBatch); err != nil {
			return nil, err
		}
	}

	// 6. Atomically persist output batches, PROCESSED events, and bipartite lineage edges
	for _, outBatch := range outputBatches {
		eventData, _ := json.Marshal(map[string]interface{}{
			"action":         "OUTPUT_CREATED",
			"inputBatchIds":  input.InputBatchIDs,
			"processingLoss": input.ProcessingLoss,
			"processDetails": input.ProcessDetails,
		})
		if _, err := createEvent(ctx, outBatch, EventProcessed, caller, string(eventData)); err != nil {
			return nil, err
		}

		// Create bipartite lineage edges: Every input connects to every output
		for _, inID := range input.InputBatchIDs {
			if _, err := createLineageEdge(ctx, inID, outBatch.BatchID, LineageActionProcessed, caller.ActorID); err != nil {
				return nil, err
			}
		}

		if err := putBatch(ctx, outBatch); err != nil {
			return nil, err
		}
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, outputBatches)
	return outputBatches, nil
}

// ==========================================
// 6. Inspector — RecordInspection & IssueCertificate
// ==========================================

// RecordInspection logs an independent inspection report.
func (c *AgroVaaniContract) RecordInspection(ctx contractapi.TransactionContextInterface, inputJSON string) (*BatchEvent, error) {
	caller, err := requireRole(ctx, RoleInspector)
	if err != nil {
		return nil, err
	}

	var input RecordInspectionInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid record inspection payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing BatchEvent
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	batch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	eventDataBytes, _ := json.Marshal(map[string]interface{}{
		"inspectionType":   input.InspectionType,
		"evidenceHash":     input.EvidenceHash,
		"inspectionResult": input.InspectionResult,
		"details":          input.Details,
	})

	event, err := createEvent(ctx, batch, EventQualityCheck, caller, string(eventDataBytes))
	if err != nil {
		return nil, err
	}

	if err := putBatch(ctx, batch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, event)
	return event, nil
}

// IssueCertificate cryptographically seals the batch state hash and evidence hash into a Certificate.
func (c *AgroVaaniContract) IssueCertificate(ctx contractapi.TransactionContextInterface, inputJSON string) (*Certificate, error) {
	caller, err := requireRole(ctx, RoleInspector)
	if err != nil {
		return nil, err
	}

	var input IssueCertificateInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid issue certificate payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Certificate
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	batch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	cert, err := issueCertificateInternal(ctx, batch, input.CertID, input.CertHash, caller)
	if err != nil {
		return nil, err
	}

	if err := putBatch(ctx, batch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, cert)
	return cert, nil
}

// ==========================================
// 7. Retailer — RetailBatch & RecordRetailSale
// ==========================================

// RetailBatch lists a manufactured product for retail sale (RET-YYYY-XXXXXX).
func (c *AgroVaaniContract) RetailBatch(ctx contractapi.TransactionContextInterface, inputJSON string) (*Batch, error) {
	caller, err := requireRole(ctx, RoleRetailer)
	if err != nil {
		return nil, err
	}

	var input RetailBatchInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid retail batch payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	parentBatch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	childBatchID, err := generateBatchID(ctx, PrefixRET)
	if err != nil {
		return nil, err
	}

	txTime, _ := getTxTimestamp(ctx)
	qty := input.Quantity
	if qty <= 0 {
		qty = parentBatch.Quantity
	}

	childBatch := &Batch{
		BatchID:        childBatchID,
		BatchType:      PrefixRET,
		CropType:       parentBatch.CropType,
		Quantity:       qty,
		Unit:           input.Unit,
		Stage:          StageRetail,
		Status:         StatusAtRetail,
		CurrentOwner:   caller.ActorID,
		ParentBatchIDs: []string{parentBatch.BatchID},
		ChildBatchIDs:  []string{},
		ProcessingLoss: 0,
		Events:         []string{},
		CreatedAt:      txTime,
		UpdatedAt:      txTime,
	}

	parentBatch.Status = StatusAtRetail
	parentBatch.ChildBatchIDs = append(parentBatch.ChildBatchIDs, childBatchID)
	parentBatch.UpdatedAt = txTime

	eventDataBytes, _ := json.Marshal(map[string]interface{}{
		"retailSku":     input.RetailSKU,
		"storeName":     input.StoreName,
		"parentBatchId": parentBatch.BatchID,
	})

	if _, err := createEvent(ctx, childBatch, EventRetailListed, caller, string(eventDataBytes)); err != nil {
		return nil, err
	}

	if _, err := createLineageEdge(ctx, parentBatch.BatchID, childBatchID, LineageActionRetail, caller.ActorID); err != nil {
		return nil, err
	}

	if err := putBatch(ctx, parentBatch); err != nil {
		return nil, err
	}
	if err := putBatch(ctx, childBatch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, childBatch)
	return childBatch, nil
}

// RecordRetailSale records final consumer purchase, transitioning batch to SOLD.
func (c *AgroVaaniContract) RecordRetailSale(ctx contractapi.TransactionContextInterface, inputJSON string) (*Batch, error) {
	caller, err := requireRole(ctx, RoleRetailer)
	if err != nil {
		return nil, err
	}

	var input RecordRetailSaleInput
	if err := json.Unmarshal([]byte(inputJSON), &input); err != nil {
		return nil, fmt.Errorf("invalid record sale payload: %w", err)
	}

	if cached, ok, err := checkIdempotency(ctx, input.TxKey); err != nil {
		return nil, err
	} else if ok {
		var existing Batch
		_ = json.Unmarshal([]byte(cached), &existing)
		return &existing, nil
	}

	batch, err := getBatch(ctx, input.BatchID)
	if err != nil {
		return nil, err
	}

	if batch.Status == StatusSold || batch.Status == StatusConsumed {
		return nil, fmt.Errorf("batch %s is already SOLD or CONSUMED", batch.BatchID)
	}

	txTime, _ := getTxTimestamp(ctx)
	batch.Status = StatusSold
	batch.Stage = StageConsumer
	batch.UpdatedAt = txTime

	eventDataBytes, _ := json.Marshal(map[string]interface{}{
		"quantity":  input.Quantity,
		"invoiceId": input.InvoiceID,
		"saleDate":  input.SaleDate,
	})

	if _, err := createEvent(ctx, batch, EventSold, caller, string(eventDataBytes)); err != nil {
		return nil, err
	}

	if err := putBatch(ctx, batch); err != nil {
		return nil, err
	}

	_ = storeIdempotencyResult(ctx, input.TxKey, batch)
	return batch, nil
}

// ==========================================
// 8. Public / Consumer Read-Only Queries
// ==========================================

// GetBatch retrieves a single batch by ID (read-only).
func (c *AgroVaaniContract) GetBatch(ctx contractapi.TransactionContextInterface, batchID string) (*Batch, error) {
	return getBatch(ctx, batchID)
}

// GetBatchEvents retrieves all historical audit trail events for a batch (read-only).
func (c *AgroVaaniContract) GetBatchEvents(ctx contractapi.TransactionContextInterface, batchID string) ([]*BatchEvent, error) {
	return getBatchEvents(ctx, batchID)
}

// GetBatchLineage reconstructs complete DAG provenance from final product back to farm roots (read-only).
func (c *AgroVaaniContract) GetBatchLineage(ctx contractapi.TransactionContextInterface, batchID string) (*LineageProvenance, error) {
	return getBatchLineage(ctx, batchID)
}

// GetCertificate retrieves a certificate by cert ID (read-only).
func (c *AgroVaaniContract) GetCertificate(ctx contractapi.TransactionContextInterface, certID string) (*Certificate, error) {
	return getCertificate(ctx, certID)
}
