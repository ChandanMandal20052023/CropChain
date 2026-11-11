package chaincode

import (
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// getCallerIdentity extracts authoritative identity and certificate attributes from the Fabric transaction context.
func getCallerIdentity(ctx contractapi.TransactionContextInterface) (*CallerIdentity, error) {
	clientIdentity := ctx.GetClientIdentity()
	if clientIdentity == nil {
		return nil, fmt.Errorf("failed to retrieve client identity from transaction context")
	}

	mspID, err := clientIdentity.GetMSPID()
	if err != nil {
		return nil, fmt.Errorf("failed to extract caller MSP ID: %w", err)
	}

	actorID, found, _ := clientIdentity.GetAttributeValue("actorId")
	if !found || actorID == "" {
		// Fallback to enrollment ID / X.509 Subject CN if attribute is not explicitly injected
		id, err := clientIdentity.GetID()
		if err == nil {
			actorID = id
		} else {
			actorID = "unknown_actor"
		}
	}

	role, found, _ := clientIdentity.GetAttributeValue("role")
	if !found || role == "" {
		// Map default role based on MSP if explicit attribute is absent
		switch mspID {
		case FarmerMSP:
			role = RoleFarmer
		case CollectionCenterMSP:
			role = RoleCollectionCenter
		case TransporterMSP:
			role = RoleTransporter
		case WarehouseMSP:
			role = RoleWarehouse
		case ManufacturerMSP:
			role = RoleManufacturer
		case InspectorMSP:
			role = RoleInspector
		case RetailerMSP:
			role = RoleRetailer
		case ConsumerMSP:
			role = RoleConsumer
		default:
			role = "unspecified"
		}
	}

	cert, err := clientIdentity.GetX509Certificate()
	certCN := ""
	if err == nil && cert != nil {
		certCN = cert.Subject.CommonName
	}

	return &CallerIdentity{
		MSP:     mspID,
		ActorID: actorID,
		Role:    role,
		CertCN:  certCN,
	}, nil
}

// requireMSP validates that the caller belongs to one of the authorized MSPs.
func requireMSP(ctx contractapi.TransactionContextInterface, allowedMSPs ...string) (*CallerIdentity, error) {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return nil, err
	}

	for _, allowed := range allowedMSPs {
		if caller.MSP == allowed {
			return caller, nil
		}
	}

	return nil, fmt.Errorf("caller MSP %s is not authorized to execute this transaction; required one of %v", caller.MSP, allowedMSPs)
}

// requireRole validates that the caller holds one of the authorized roles.
func requireRole(ctx contractapi.TransactionContextInterface, allowedRoles ...string) (*CallerIdentity, error) {
	caller, err := getCallerIdentity(ctx)
	if err != nil {
		return nil, err
	}

	for _, allowed := range allowedRoles {
		if caller.Role == allowed {
			return caller, nil
		}
	}

	return nil, fmt.Errorf("caller role '%s' (MSP: %s) is not authorized; required one of %v", caller.Role, caller.MSP, allowedRoles)
}

// requireActor validates that the caller's actor ID matches the expected actor ID.
func requireActor(caller *CallerIdentity, expectedActorID string) error {
	if expectedActorID != "" && caller.ActorID != expectedActorID {
		return fmt.Errorf("caller actor ID '%s' does not match required actor ID '%s'", caller.ActorID, expectedActorID)
	}
	return nil
}

// requireBatchOwnership validates that the caller is currently entitled to act on the batch.
func requireBatchOwnership(batch *Batch, caller *CallerIdentity) error {
	if batch.CurrentOwner != "" && batch.CurrentOwner != caller.ActorID && batch.CurrentOwner != caller.MSP {
		return fmt.Errorf("caller '%s' (MSP: %s) is not the current owner of batch %s (current owner: %s)",
			caller.ActorID, caller.MSP, batch.BatchID, batch.CurrentOwner)
	}
	return nil
}
