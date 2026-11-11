package chaincode

// AgroVaani Chaincode Constants

// MSP IDs for the 8 Organizations
const (
	FarmerMSP           = "AgroVaaniFarmerMSP"
	CollectionCenterMSP = "AgroVaaniCollectionCenterMSP"
	TransporterMSP      = "AgroVaaniTransporterMSP"
	WarehouseMSP        = "AgroVaaniWarehouseMSP"
	ManufacturerMSP     = "AgroVaaniManufacturerMSP"
	InspectorMSP        = "AgroVaaniInspectorMSP"
	RetailerMSP         = "AgroVaaniRetailerMSP"
	ConsumerMSP         = "AgroVaaniConsumerMSP"
)

// Roles for Chaincode Authorization
const (
	RoleFarmer           = "farmer"
	RoleCollectionCenter = "collection_center"
	RoleTransporter      = "transporter"
	RoleWarehouse        = "warehouse"
	RoleManufacturer     = "manufacturer"
	RoleInspector        = "inspector"
	RoleRetailer         = "retailer"
	RoleConsumer         = "consumer"
)

// Batch Prefixes
const (
	PrefixRAW = "RAW"
	PrefixCC  = "CC"
	PrefixWH  = "WH"
	PrefixMFG = "MFG"
	PrefixRET = "RET"
)

// World State Sequence Counter Keys
const (
	SeqCtrRAW = "SEQCTR_RAW"
	SeqCtrCC  = "SEQCTR_CC"
	SeqCtrWH  = "SEQCTR_WH"
	SeqCtrMFG = "SEQCTR_MFG"
	SeqCtrRET = "SEQCTR_RET"
)

// Supply Chain Stages
const (
	StageFarm             = "FARM"
	StageCollectionCenter = "COLLECTION_CENTER"
	StageTransport        = "TRANSPORT"
	StageWarehouse        = "WAREHOUSE"
	StageManufacturing    = "MANUFACTURING"
	StageRetail           = "RETAIL"
	StageConsumer         = "CONSUMER"
)

// Batch Lifecycle Statuses
const (
	StatusPending        = "PENDING"
	StatusQualityChecked = "QUALITY_CHECKED"
	StatusAccepted       = "ACCEPTED"
	StatusRejected       = "REJECTED"
	StatusPacked         = "PACKED"
	StatusInTransit      = "IN_TRANSIT"
	StatusInWarehouse    = "IN_WAREHOUSE"
	StatusManufactured   = "MANUFACTURED"
	StatusConsumed       = "CONSUMED"
	StatusAtRetail       = "AT_RETAIL"
	StatusSold           = "SOLD"
)

// Immutable Event Types
const (
	EventBatchCreated        = "BATCH_CREATED"
	EventQualityCheck        = "QUALITY_CHECK"
	EventAccepted            = "ACCEPTED"
	EventRejected            = "REJECTED"
	EventPacked              = "PACKED"
	EventTransferred         = "TRANSFERRED"
	EventReceivedAtWarehouse = "RECEIVED_AT_WAREHOUSE"
	EventProcessed           = "PROCESSED"
	EventCertificateIssued   = "CERTIFICATE_ISSUED"
	EventRetailListed        = "RETAIL_LISTED"
	EventSold                = "SOLD"
)

// Lineage Edge Actions
const (
	LineageActionPacked    = "PACKED"
	LineageActionStored    = "STORED"
	LineageActionProcessed = "PROCESSED"
	LineageActionRetail    = "RETAIL_LISTED"
)
