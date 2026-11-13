package tests

import (
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/json"
	"testing"
	"time"

	"github.com/agrovaani/chaincode/chaincode"
	"github.com/hyperledger/fabric-chaincode-go/v2/pkg/cid"
	"github.com/hyperledger/fabric-chaincode-go/v2/shim"
	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
	"github.com/hyperledger/fabric-protos-go-apiv2/ledger/queryresult"
	"github.com/hyperledger/fabric-protos-go-apiv2/peer"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"google.golang.org/protobuf/types/known/timestamppb"
)

// --- Mock Chaincode Stub & Client Identity ---

type MockChaincodeStub struct {
	mock.Mock
	state map[string][]byte
}

func NewMockChaincodeStub() *MockChaincodeStub {
	return &MockChaincodeStub{
		state: make(map[string][]byte),
	}
}

func (m *MockChaincodeStub) GetState(key string) ([]byte, error) {
	val, exists := m.state[key]
	if !exists {
		return nil, nil
	}
	return val, nil
}

func (m *MockChaincodeStub) PutState(key string, value []byte) error {
	m.state[key] = value
	return nil
}

func (m *MockChaincodeStub) DelState(key string) error {
	delete(m.state, key)
	return nil
}

func (m *MockChaincodeStub) SetEvent(name string, payload []byte) error {
	return nil
}

func (m *MockChaincodeStub) GetTxTimestamp() (*timestamppb.Timestamp, error) {
	now := time.Date(2026, 8, 23, 12, 0, 0, 0, time.UTC)
	return timestamppb.New(now), nil
}

func (m *MockChaincodeStub) GetQueryResult(query string) (shim.StateQueryIteratorInterface, error) {
	return &MockIterator{closed: false}, nil
}

func (m *MockChaincodeStub) GetCreator() ([]byte, error)                             { return []byte("mock_creator"), nil }
func (m *MockChaincodeStub) GetArgs() [][]byte                                        { return nil }
func (m *MockChaincodeStub) GetStringArgs() []string                                  { return nil }
func (m *MockChaincodeStub) GetFunctionAndParameters() (string, []string)             { return "", nil }
func (m *MockChaincodeStub) GetArgsSlice() ([]byte, error)                           { return nil, nil }
func (m *MockChaincodeStub) GetTxID() string                                          { return "mock_tx_id_12345" }
func (m *MockChaincodeStub) GetChannelID() string                                     { return "agrovaani-channel" }
func (m *MockChaincodeStub) InvokeChaincode(string, [][]byte, string) *peer.Response  { return &peer.Response{} }
func (m *MockChaincodeStub) GetStateByRange(string, string) (shim.StateQueryIteratorInterface, error) {
	return &MockIterator{}, nil
}
func (m *MockChaincodeStub) GetStateByRangeWithPagination(string, string, int32, string) (shim.StateQueryIteratorInterface, *peer.QueryResponseMetadata, error) {
	return &MockIterator{}, nil, nil
}
func (m *MockChaincodeStub) GetStateByPartialCompositeKey(string, []string) (shim.StateQueryIteratorInterface, error) {
	return &MockIterator{}, nil
}
func (m *MockChaincodeStub) GetStateByPartialCompositeKeyWithPagination(string, []string, int32, string) (shim.StateQueryIteratorInterface, *peer.QueryResponseMetadata, error) {
	return &MockIterator{}, nil, nil
}
func (m *MockChaincodeStub) CreateCompositeKey(string, []string) (string, error) { return "", nil }
func (m *MockChaincodeStub) SplitCompositeKey(string) (string, []string, error)  { return "", nil, nil }
func (m *MockChaincodeStub) GetQueryResultWithPagination(string, int32, string) (shim.StateQueryIteratorInterface, *peer.QueryResponseMetadata, error) {
	return &MockIterator{}, nil, nil
}
func (m *MockChaincodeStub) GetHistoryForKey(string) (shim.HistoryQueryIteratorInterface, error) {
	return nil, nil
}
func (m *MockChaincodeStub) GetPrivateData(string, string) ([]byte, error)            { return nil, nil }
func (m *MockChaincodeStub) GetPrivateDataHash(string, string) ([]byte, error)        { return nil, nil }
func (m *MockChaincodeStub) PutPrivateData(string, string, []byte) error              { return nil }
func (m *MockChaincodeStub) DelPrivateData(string, string) error                      { return nil }
func (m *MockChaincodeStub) PurgePrivateData(string, string) error                    { return nil }
func (m *MockChaincodeStub) SetPrivateDataValidationParameter(string, string, []byte) error {
	return nil
}
func (m *MockChaincodeStub) GetPrivateDataValidationParameter(string, string) ([]byte, error) {
	return nil, nil
}
func (m *MockChaincodeStub) SetStateValidationParameter(string, []byte) error { return nil }
func (m *MockChaincodeStub) GetStateValidationParameter(string) ([]byte, error) {
	return nil, nil
}
func (m *MockChaincodeStub) GetPrivateDataByRange(string, string, string) (shim.StateQueryIteratorInterface, error) {
	return nil, nil
}
func (m *MockChaincodeStub) GetPrivateDataByPartialCompositeKey(string, string, []string) (shim.StateQueryIteratorInterface, error) {
	return nil, nil
}
func (m *MockChaincodeStub) GetPrivateDataQueryResult(string, string) (shim.StateQueryIteratorInterface, error) {
	return nil, nil
}
func (m *MockChaincodeStub) GetTransient() (map[string][]byte, error) { return nil, nil }
func (m *MockChaincodeStub) GetBinding() ([]byte, error)              { return nil, nil }
func (m *MockChaincodeStub) GetDecorations() map[string][]byte        { return nil }
func (m *MockChaincodeStub) GetSignedProposal() (*peer.SignedProposal, error) {
	return nil, nil
}

type MockIterator struct {
	closed bool
}

func (it *MockIterator) HasNext() bool                                  { return false }
func (it *MockIterator) Next() (*queryresult.KV, error)                 { return nil, nil }
func (it *MockIterator) Close() error                                   { it.closed = true; return nil }

type MockClientIdentity struct {
	mspID      string
	actorID    string
	role       string
	commonName string
}

func (ci *MockClientIdentity) GetID() (string, error)                   { return ci.actorID, nil }
func (ci *MockClientIdentity) GetMSPID() (string, error)                { return ci.mspID, nil }
func (ci *MockClientIdentity) GetAttributeValue(attrName string) (string, bool, error) {
	switch attrName {
	case "role":
		return ci.role, true, nil
	case "actorId":
		return ci.actorID, true, nil
	}
	return "", false, nil
}
func (ci *MockClientIdentity) AssertAttributeValue(string, string) error { return nil }
func (ci *MockClientIdentity) GetX509Certificate() (*x509.Certificate, error) {
	return &x509.Certificate{
		Subject: pkix.Name{
			CommonName: ci.commonName,
		},
	}, nil
}

type MockTransactionContext struct {
	contractapi.TransactionContext
	stub           *MockChaincodeStub
	clientIdentity cid.ClientIdentity
}

func (tc *MockTransactionContext) GetStub() shim.ChaincodeStubInterface {
	return tc.stub
}

func (tc *MockTransactionContext) GetClientIdentity() cid.ClientIdentity {
	return tc.clientIdentity
}

func createTestContext(mspID, role, actorID string) (*MockTransactionContext, *MockChaincodeStub) {
	stub := NewMockChaincodeStub()
	identity := &MockClientIdentity{
		mspID:      mspID,
		role:       role,
		actorID:    actorID,
		commonName: actorID,
	}
	return &MockTransactionContext{stub: stub, clientIdentity: identity}, stub
}

// ==========================================
// TEST SUITE: Core Business Invariants & Rules
// ==========================================

func TestFarmerCreateBatchAndSequenceIncrement(t *testing.T) {
	ctx, _ := createTestContext(chaincode.FarmerMSP, chaincode.RoleFarmer, "FARMER-001")
	contract := new(chaincode.AgroVaaniContract)

	input1 := chaincode.CreateBatchInput{
		TxKey:       "tx_create_1",
		CropType:    "Wheat",
		Quantity:    500.0,
		Unit:        "kg",
		FarmID:      "FARM-PUNJAB-12",
		FarmerID:    "FARMER-001",
		HarvestDate: "2026-08-20",
		LandInfo:    "Plot 4B",
	}
	inputBytes1, _ := json.Marshal(input1)

	batch1, err := contract.CreateBatch(ctx, string(inputBytes1))
	assert.NoError(t, err)
	assert.NotNil(t, batch1)
	assert.Equal(t, "RAW-2026-000001", batch1.BatchID)
	assert.Equal(t, "Wheat", batch1.CropType)
	assert.Equal(t, 500.0, batch1.Quantity)
	assert.Equal(t, chaincode.StatusPending, batch1.Status)
	assert.Equal(t, chaincode.StageFarm, batch1.Stage)
	assert.Equal(t, 1, len(batch1.Events))

	// Create second batch and verify sequence increments atomically to RAW-2026-000002
	input2 := chaincode.CreateBatchInput{
		TxKey:    "tx_create_2",
		CropType: "Basmati Rice",
		Quantity: 300.0,
		Unit:     "kg",
		FarmerID: "FARMER-001",
	}
	inputBytes2, _ := json.Marshal(input2)

	batch2, err := contract.CreateBatch(ctx, string(inputBytes2))
	assert.NoError(t, err)
	assert.NotNil(t, batch2)
	assert.Equal(t, "RAW-2026-000002", batch2.BatchID)
}

func TestUnauthorizedMSPAndRoleRejection(t *testing.T) {
	// Manufacturer trying to call Farmer CreateBatch
	ctx, _ := createTestContext(chaincode.ManufacturerMSP, chaincode.RoleManufacturer, "MFG-001")
	contract := new(chaincode.AgroVaaniContract)

	input := chaincode.CreateBatchInput{
		TxKey:    "tx_unauth_1",
		CropType: "Wheat",
		Quantity: 100.0,
	}
	inputBytes, _ := json.Marshal(input)

	batch, err := contract.CreateBatch(ctx, string(inputBytes))
	assert.Error(t, err)
	assert.Nil(t, batch)
	assert.Contains(t, err.Error(), "not authorized")
}

func TestCollectionCenterVerificationAndPacking(t *testing.T) {
	farmerCtx, stub := createTestContext(chaincode.FarmerMSP, chaincode.RoleFarmer, "FARMER-001")
	contract := new(chaincode.AgroVaaniContract)

	// 1. Farmer creates RAW batch
	fInput := chaincode.CreateBatchInput{
		TxKey:    "tx_farmer_1",
		CropType: "Wheat",
		Quantity: 500.0,
		Unit:     "kg",
	}
	fBytes, _ := json.Marshal(fInput)
	rawBatch, err := contract.CreateBatch(farmerCtx, string(fBytes))
	assert.NoError(t, err)

	// 2. Collection Center verifies batch (QUALITY_CHECK)
	ccCtx := &MockTransactionContext{
		stub: stub,
		clientIdentity: &MockClientIdentity{
			mspID:   chaincode.CollectionCenterMSP,
			role:    chaincode.RoleCollectionCenter,
			actorID: "CC-LUDHIANA-01",
		},
	}

	vInput := chaincode.VerifyBatchInput{
		TxKey:            "tx_verify_1",
		BatchID:          rawBatch.BatchID,
		ActualQuantity:   500.0,
		MoistureContent:  11.5,
		QualityGrade:     "Grade A",
		ForeignMaterial:  0.2,
		InspectionResult: "PASSED",
	}
	vBytes, _ := json.Marshal(vInput)
	verifiedBatch, err := contract.VerifyBatch(ccCtx, string(vBytes))
	assert.NoError(t, err)
	assert.Equal(t, chaincode.StatusQualityChecked, verifiedBatch.Status)

	// 3. Collection Center accepts batch (ACCEPTED)
	aInput := chaincode.AcceptBatchInput{
		TxKey:   "tx_accept_1",
		BatchID: rawBatch.BatchID,
		Notes:   "Premium harvest quality approved",
	}
	aBytes, _ := json.Marshal(aInput)
	acceptedBatch, err := contract.AcceptBatch(ccCtx, string(aBytes))
	assert.NoError(t, err)
	assert.Equal(t, chaincode.StatusAccepted, acceptedBatch.Status)

	// 4. Collection Center packs batch into CC-2026-000001
	pInput := chaincode.PackBatchInput{
		TxKey:       "tx_pack_1",
		BatchID:     rawBatch.BatchID,
		Quantity:    500.0,
		Unit:        "kg",
		PackageType: "Jute Sacks 50kg x 10",
	}
	pBytes, _ := json.Marshal(pInput)
	ccBatch, err := contract.PackBatch(ccCtx, string(pBytes))
	assert.NoError(t, err)
	assert.Equal(t, "CC-2026-000001", ccBatch.BatchID)
	assert.Equal(t, []string{"RAW-2026-000001"}, ccBatch.ParentBatchIDs)
	assert.Equal(t, chaincode.StatusPacked, ccBatch.Status)
}

func TestQuantityConservationEnforcementInProcessing(t *testing.T) {
	ctx, stub := createTestContext(chaincode.ManufacturerMSP, chaincode.RoleManufacturer, "MFG-FACTORY-01")
	contract := new(chaincode.AgroVaaniContract)

	// Seed 3 input batches in stub
	batchA := &chaincode.Batch{
		BatchID:   "WH-2026-000001",
		BatchType: "WH",
		CropType:  "Wheat Flour",
		Quantity:  300.0,
		Unit:      "kg",
		Status:    chaincode.StatusInWarehouse,
	}
	batchB := &chaincode.Batch{
		BatchID:   "WH-2026-000002",
		BatchType: "WH",
		CropType:  "Sugar",
		Quantity:  150.0,
		Unit:      "kg",
		Status:    chaincode.StatusInWarehouse,
	}
	batchC := &chaincode.Batch{
		BatchID:   "WH-2026-000003",
		BatchType: "WH",
		CropType:  "Milk Powder",
		Quantity:  50.0,
		Unit:      "kg",
		Status:    chaincode.StatusInWarehouse,
	}
	_ = stub.PutState("BATCH_WH-2026-000001", mustMarshal(batchA))
	_ = stub.PutState("BATCH_WH-2026-000002", mustMarshal(batchB))
	_ = stub.PutState("BATCH_WH-2026-000003", mustMarshal(batchC))

	// Total Input Quantity = 300 + 150 + 50 = 500.0 kg

	// Test Case 1: Conservation Equation FAILS (Outputs 480 + Loss 10 != 500) -> MUST REJECT
	invalidInput := chaincode.ProcessBatchInput{
		TxKey:         "tx_proc_invalid",
		InputBatchIDs: []string{"WH-2026-000001", "WH-2026-000002", "WH-2026-000003"},
		Outputs: []chaincode.OutputBatchSpec{
			{ProductType: "Biscuits", Quantity: 480.0, Unit: "kg"},
		},
		ProcessingLoss: 10.0, // 480 + 10 = 490 != 500
	}
	invalidBytes, _ := json.Marshal(invalidInput)
	_, err := contract.ProcessBatch(ctx, string(invalidBytes))
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "quantity conservation failed")

	// Test Case 2: Conservation Equation PASSES (Outputs 480 + Loss 20 == 500) -> MUST SUCCEED
	validInput := chaincode.ProcessBatchInput{
		TxKey:         "tx_proc_valid",
		InputBatchIDs: []string{"WH-2026-000001", "WH-2026-000002", "WH-2026-000003"},
		Outputs: []chaincode.OutputBatchSpec{
			{ProductType: "Biscuits Grade A", Quantity: 300.0, Unit: "kg"},
			{ProductType: "Biscuits Grade B", Quantity: 180.0, Unit: "kg"},
		},
		ProcessingLoss: 20.0, // 300 + 180 + 20 = 500.0 == 500.0
	}
	validBytes, _ := json.Marshal(validInput)
	outputs, err := contract.ProcessBatch(ctx, string(validBytes))
	assert.NoError(t, err)
	assert.Equal(t, 2, len(outputs))
	assert.Equal(t, "MFG-2026-000001", outputs[0].BatchID)
	assert.Equal(t, "MFG-2026-000002", outputs[1].BatchID)
	assert.Equal(t, []string{"WH-2026-000001", "WH-2026-000002", "WH-2026-000003"}, outputs[0].ParentBatchIDs)

	// Verify all input batches are marked CONSUMED
	savedA, _ := stub.GetState("BATCH_WH-2026-000001")
	var updatedA chaincode.Batch
	_ = json.Unmarshal(savedA, &updatedA)
	assert.Equal(t, chaincode.StatusConsumed, updatedA.Status)
	assert.Contains(t, updatedA.ChildBatchIDs, "MFG-2026-000001")
	assert.Contains(t, updatedA.ChildBatchIDs, "MFG-2026-000002")

	// Test Case 3: Reusing consumed inputs MUST FAIL
	reuseInput := chaincode.ProcessBatchInput{
		TxKey:         "tx_proc_reuse",
		InputBatchIDs: []string{"WH-2026-000001"},
		Outputs: []chaincode.OutputBatchSpec{
			{ProductType: "More Biscuits", Quantity: 300.0, Unit: "kg"},
		},
		ProcessingLoss: 0.0,
	}
	reuseBytes, _ := json.Marshal(reuseInput)
	_, err = contract.ProcessBatch(ctx, string(reuseBytes))
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "already CONSUMED")
}

func TestIdempotencyHandling(t *testing.T) {
	ctx, _ := createTestContext(chaincode.FarmerMSP, chaincode.RoleFarmer, "FARMER-001")
	contract := new(chaincode.AgroVaaniContract)

	input := chaincode.CreateBatchInput{
		TxKey:    "idemp_unique_key_001",
		CropType: "Organic Cotton",
		Quantity: 1000.0,
		Unit:     "kg",
	}
	inputBytes, _ := json.Marshal(input)

	// First submission creates the batch
	batchFirst, err := contract.CreateBatch(ctx, string(inputBytes))
	assert.NoError(t, err)
	assert.Equal(t, "RAW-2026-000001", batchFirst.BatchID)

	// Resubmitting same transaction with same txKey returns identical result without incrementing counter
	batchSecond, err := contract.CreateBatch(ctx, string(inputBytes))
	assert.NoError(t, err)
	assert.Equal(t, batchFirst.BatchID, batchSecond.BatchID)
}

func TestCertificateDeterministicHashing(t *testing.T) {
	ctx, stub := createTestContext(chaincode.InspectorMSP, chaincode.RoleInspector, "INSPECTOR-GOV-01")
	contract := new(chaincode.AgroVaaniContract)

	batch := &chaincode.Batch{
		BatchID:        "MFG-2026-000001",
		BatchType:      "MFG",
		CropType:       "Biscuits",
		Quantity:       480.0,
		Unit:           "kg",
		Stage:          chaincode.StageManufacturing,
		Status:         chaincode.StatusManufactured,
		CurrentOwner:   "MFG-FACTORY-01",
		ParentBatchIDs: []string{"WH-2026-000001"},
		ChildBatchIDs:  []string{},
		CreatedAt:      "2026-08-23T12:00:00Z",
	}
	_ = stub.PutState("BATCH_MFG-2026-000001", mustMarshal(batch))

	certInput := chaincode.IssueCertificateInput{
		TxKey:          "tx_cert_01",
		BatchID:        "MFG-2026-000001",
		CertID:         "FSSAI-CERT-2026-0099",
		CertHash:       "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
		CertType:       "Food Safety & Organic Standards",
		ValidityPeriod: "2026-2028",
	}
	certBytes, _ := json.Marshal(certInput)

	cert, err := contract.IssueCertificate(ctx, string(certBytes))
	assert.NoError(t, err)
	assert.NotNil(t, cert)
	assert.Equal(t, "FSSAI-CERT-2026-0099", cert.CertID)
	assert.NotEmpty(t, cert.BatchStateHash)
	assert.Equal(t, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", cert.CertHash)
}

func mustMarshal(v interface{}) []byte {
	b, _ := json.Marshal(v)
	return b
}
