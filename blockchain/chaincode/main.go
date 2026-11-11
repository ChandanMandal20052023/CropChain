package main

import (
	"log"

	"github.com/agrovaani/chaincode/chaincode"
	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

func main() {
	agroVaaniContract := new(chaincode.AgroVaaniContract)

	cc, err := contractapi.NewChaincode(agroVaaniContract)
	if err != nil {
		log.Panicf("Error creating AgroVaani chaincode: %v", err)
	}

	if err := cc.Start(); err != nil {
		log.Panicf("Error starting AgroVaani chaincode server: %v", err)
	}
}
