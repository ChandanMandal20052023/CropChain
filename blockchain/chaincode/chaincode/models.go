package chaincode

// Batch represents the primary supply chain unit in AgroVaani world state.
type Batch struct {
	BatchID        string   `json:"batchId"`
	BatchType      string   `json:"batchType"`
	CropType       string   `json:"cropType"`
	Quantity       float64  `json:"quantity"`
	Unit           string   `json:"unit"`
	Stage          string   `json:"stage"`
	Status         string   `json:"status"`
	CurrentOwner   string   `json:"currentOwner"`
	ParentBatchIDs []string `json:"parentBatchIds"`
	ChildBatchIDs  []string `json:"childBatchIds"`
	ProcessingLoss float64  `json:"processingLoss"`
	Events         []string `json:"events"`
	CreatedAt      string   `json:"createdAt"`
	UpdatedAt      string   `json:"updatedAt"`
}

// BatchEvent represents an immutable append-only event recording a state transition or action.
type BatchEvent struct {
	EventID   string `json:"eventId"`
	BatchID   string `json:"batchId"`
	EventType string `json:"eventType"`
	ActorID   string `json:"actorId"`
	ActorRole string `json:"actorRole"`
	OrgMSP    string `json:"orgMsp"`
	Data      string `json:"data"`
	Timestamp string `json:"timestamp"`
}

// LineageEdge represents a single directed relationship in the DAG.
type LineageEdge struct {
	FromBatchID string `json:"fromBatchId"`
	ToBatchID   string `json:"toBatchId"`
	Action      string `json:"action"`
	ActorID     string `json:"actorId"`
	Timestamp   string `json:"timestamp"`
}

// LineageGraph represents the set of edges associated with a batch.
type LineageGraph struct {
	BatchID string        `json:"batchId"`
	Edges   []LineageEdge `json:"edges"`
}

// Certificate represents a quality or compliance certificate cryptographically bound to batch state.
type Certificate struct {
	CertID         string `json:"certId"`
	BatchID        string `json:"batchId"`
	IssuedBy       string `json:"issuedBy"`
	CertHash       string `json:"certHash"`
	BatchStateHash string `json:"batchStateHash"`
	IssuedAt       string `json:"issuedAt"`
}

// CallerIdentity holds verified identity information extracted from client certificate.
type CallerIdentity struct {
	MSP     string `json:"msp"`
	ActorID string `json:"actorId"`
	Role    string `json:"role"`
	CertCN  string `json:"certCn"`
}

// IdempotencyRecord stores previously executed transaction output.
type IdempotencyRecord struct {
	TxKey     string `json:"txKey"`
	Result    string `json:"result"`
	Timestamp string `json:"timestamp"`
}

// --- Request DTOs ---

type CreateBatchInput struct {
	TxKey         string  `json:"txKey"`
	CropType      string  `json:"cropType"`
	Quantity      float64 `json:"quantity"`
	Unit          string  `json:"unit"`
	FarmID        string  `json:"farmId"`
	FarmerID      string  `json:"farmerId"`
	HarvestDate   string  `json:"harvestDate"`
	LandInfo      string  `json:"landInfo"`
	Certification string  `json:"certification"`
	CropDetails   string  `json:"cropDetails"`
}

type VerifyBatchInput struct {
	TxKey            string  `json:"txKey"`
	BatchID          string  `json:"batchId"`
	ActualQuantity   float64 `json:"actualQuantity"`
	MoistureContent  float64 `json:"moistureContent"`
	QualityGrade     string  `json:"qualityGrade"`
	ForeignMaterial  float64 `json:"foreignMaterial"`
	InspectionResult string  `json:"inspectionResult"`
	Notes            string  `json:"notes"`
}

type AcceptBatchInput struct {
	TxKey   string `json:"txKey"`
	BatchID string `json:"batchId"`
	Notes   string `json:"notes"`
}

type RejectBatchInput struct {
	TxKey   string `json:"txKey"`
	BatchID string `json:"batchId"`
	Reason  string `json:"reason"`
}

type PackBatchInput struct {
	TxKey       string  `json:"txKey"`
	BatchID     string  `json:"batchId"` // RAW parent batch ID
	Quantity    float64 `json:"quantity"`
	Unit        string  `json:"unit"`
	PackageType string  `json:"packageType"`
	Notes       string  `json:"notes"`
}

type TransferBatchInput struct {
	TxKey         string `json:"txKey"`
	BatchID       string `json:"batchId"`
	ToActorID     string `json:"toActorId"`
	ToOrgMSP      string `json:"toOrgMsp"`
	VehicleNumber string `json:"vehicleNumber"`
	RouteDetails  string `json:"routeDetails"`
}

type StoreBatchInput struct {
	TxKey          string  `json:"txKey"`
	BatchID        string  `json:"batchId"` // CC parent batch ID
	WarehouseID    string  `json:"warehouseId"`
	StorageSection string  `json:"storageSection"`
	VerifiedWeight float64 `json:"verifiedWeight"`
	Condition      string  `json:"condition"`
}

type OutputBatchSpec struct {
	BatchType   string  `json:"batchType"`
	ProductType string  `json:"productType"`
	Quantity    float64 `json:"quantity"`
	Unit        string  `json:"unit"`
}

type ProcessBatchInput struct {
	TxKey          string            `json:"txKey"`
	InputBatchIDs  []string          `json:"inputBatchIds"`
	Outputs        []OutputBatchSpec `json:"outputs"`
	ProcessingLoss float64           `json:"processingLoss"`
	ProcessDetails string            `json:"processDetails"`
}

type RecordInspectionInput struct {
	TxKey            string `json:"txKey"`
	BatchID          string `json:"batchId"`
	InspectionType   string `json:"inspectionType"`
	EvidenceHash     string `json:"evidenceHash"`
	InspectionResult string `json:"inspectionResult"`
	Details          string `json:"details"`
}

type IssueCertificateInput struct {
	TxKey          string `json:"txKey"`
	BatchID        string `json:"batchId"`
	CertID         string `json:"certId"`
	CertHash       string `json:"certHash"`
	CertType       string `json:"certType"`
	ValidityPeriod string `json:"validityPeriod"`
}

type RetailBatchInput struct {
	TxKey     string  `json:"txKey"`
	BatchID   string  `json:"batchId"` // MFG parent batch ID
	Quantity  float64 `json:"quantity"`
	Unit      string  `json:"unit"`
	RetailSKU string  `json:"retailSku"`
	StoreName string  `json:"storeName"`
}

type RecordRetailSaleInput struct {
	TxKey     string  `json:"txKey"`
	BatchID   string  `json:"batchId"`
	Quantity  float64 `json:"quantity"`
	InvoiceID string  `json:"invoiceId"`
	SaleDate  string  `json:"saleDate"`
}

// LineageProvenance is the comprehensive DAG backward traversal output for consumer QR scans.
type LineageProvenance struct {
	TargetBatch  *Batch        `json:"targetBatch"`
	AllBatches   []*Batch      `json:"allBatches"`
	Edges        []LineageEdge `json:"edges"`
	Events       []*BatchEvent `json:"events"`
	Certificates []*Certificate `json:"certificates"`
}
