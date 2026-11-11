package chaincode

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// calculateBatchStateHash generates a deterministic SHA-256 hash of the batch state.
// Uses canonical field serialization to guarantee reproducibility across nodes and languages.
func calculateBatchStateHash(batch *Batch) string {
	if batch == nil {
		return ""
	}

	parents := append([]string(nil), batch.ParentBatchIDs...)
	sort.Strings(parents)

	children := append([]string(nil), batch.ChildBatchIDs...)
	sort.Strings(children)

	canonicalRepresentation := fmt.Sprintf(
		"batchId:%s|type:%s|crop:%s|qty:%.4f|unit:%s|stage:%s|status:%s|owner:%s|parents:%s|children:%s|loss:%.4f|created:%s",
		batch.BatchID,
		batch.BatchType,
		batch.CropType,
		batch.Quantity,
		batch.Unit,
		batch.Stage,
		batch.Status,
		batch.CurrentOwner,
		strings.Join(parents, ","),
		strings.Join(children, ","),
		batch.ProcessingLoss,
		batch.CreatedAt,
	)

	hash := sha256.Sum256([]byte(canonicalRepresentation))
	return hex.EncodeToString(hash[:])
}

// issueCertificateInternal performs the state-persisting logic for issuing a certificate.
func issueCertificateInternal(ctx contractapi.TransactionContextInterface, batch *Batch, certID, certHash string, caller *CallerIdentity) (*Certificate, error) {
	if certID == "" {
		return nil, fmt.Errorf("certId cannot be empty")
	}

	// Verify certificate does not already exist
	certKey := fmt.Sprintf("CERT_%s", certID)
	existing, err := ctx.GetStub().GetState(certKey)
	if err != nil {
		return nil, fmt.Errorf("failed checking certificate key: %w", err)
	}
	if len(existing) > 0 {
		return nil, fmt.Errorf("certificate with ID '%s' already exists", certID)
	}

	stateHash := calculateBatchStateHash(batch)
	timestamp, err := getTxTimestamp(ctx)
	if err != nil {
		return nil, err
	}

	certificate := &Certificate{
		CertID:         certID,
		BatchID:        batch.BatchID,
		IssuedBy:       caller.ActorID,
		CertHash:       certHash,
		BatchStateHash: stateHash,
		IssuedAt:       timestamp,
	}

	certBytes, err := json.Marshal(certificate)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal certificate: %w", err)
	}

	if err := ctx.GetStub().PutState(certKey, certBytes); err != nil {
		return nil, fmt.Errorf("failed to write certificate to world state: %w", err)
	}

	// Index certificate under batch
	batchCertsKey := fmt.Sprintf("BATCH_CERTS_%s", batch.BatchID)
	var certList []string
	if data, err := ctx.GetStub().GetState(batchCertsKey); err == nil && len(data) > 0 {
		_ = json.Unmarshal(data, &certList)
	}
	certList = append(certList, certID)
	listBytes, _ := json.Marshal(certList)
	_ = ctx.GetStub().PutState(batchCertsKey, listBytes)

	// Append CERTIFICATE_ISSUED event to the batch
	eventData := fmt.Sprintf(`{"certId":"%s","certHash":"%s","batchStateHash":"%s"}`, certID, certHash, stateHash)
	if _, err := createEvent(ctx, batch, EventCertificateIssued, caller, eventData); err != nil {
		return nil, fmt.Errorf("failed to create CERTIFICATE_ISSUED event: %w", err)
	}

	return certificate, nil
}

// getCertificate retrieves a Certificate by its CertID.
func getCertificate(ctx contractapi.TransactionContextInterface, certID string) (*Certificate, error) {
	if certID == "" {
		return nil, fmt.Errorf("certId cannot be empty")
	}

	certKey := fmt.Sprintf("CERT_%s", certID)
	data, err := ctx.GetStub().GetState(certKey)
	if err != nil {
		return nil, fmt.Errorf("failed to read certificate %s: %w", certID, err)
	}
	if len(data) == 0 {
		return nil, fmt.Errorf("certificate '%s' not found", certID)
	}

	var cert Certificate
	if err := json.Unmarshal(data, &cert); err != nil {
		return nil, fmt.Errorf("failed to deserialize certificate: %w", err)
	}

	return &cert, nil
}

// getCertificatesForBatch retrieves all certificates bound to a specific batch.
func getCertificatesForBatch(ctx contractapi.TransactionContextInterface, batchID string) ([]*Certificate, error) {
	batchCertsKey := fmt.Sprintf("BATCH_CERTS_%s", batchID)
	data, err := ctx.GetStub().GetState(batchCertsKey)
	if err != nil || len(data) == 0 {
		return []*Certificate{}, nil
	}

	var certIDs []string
	if err := json.Unmarshal(data, &certIDs); err != nil {
		return []*Certificate{}, nil
	}

	var certs []*Certificate
	for _, cid := range certIDs {
		c, err := getCertificate(ctx, cid)
		if err == nil && c != nil {
			certs = append(certs, c)
		}
	}

	return certs, nil
}

// SatyaTraceExtension provides an architectural extension point for off-chain inspection/AI evidence verification.
type SatyaTraceExtension interface {
	VerifyEvidenceHash(evidenceHash string, documentMetadata string) bool
}
