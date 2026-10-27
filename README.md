# CropChain

CropChain is a planned blockchain-based agriculture and food supply chain management system. Its intended goal is farm-to-fork crop traceability for participants including farmers, suppliers, warehouses, transporters, processors, inspectors, retailers, and consumers.

This repository currently contains the initial project scaffold only. Application behavior, APIs, user interfaces, smart contracts, machine-learning models, and database schemas have not been implemented.

## Technology stack

- **Frontend:** HTML5, CSS3, and vanilla JavaScript
- **Backend:** Python, Django, and Django REST Framework
- **Database:** PostgreSQL
- **Blockchain:** Hyperledger Fabric with Go chaincode and Fabric Gateway

## Repository structure

- `frontend/` — static frontend assets and role-oriented page areas
- `backend/` — Django project areas, REST backend modules, and requirements
- `blockchain/` — Fabric network configuration areas, chaincode areas, and gateway integration
- `tests/` — integration, end-to-end, and performance test areas
- `docs/` — architecture, API, database, decisions, diagrams, research, and reports
- `.github/workflows/` — future GitHub Actions workflows

Empty directories are tracked with `.gitkeep` files. Add project-specific documentation and implementation as modules are developed; avoid committing secrets, generated credentials, or local environment files.

## Future contribution workflow

1. Select an agreed module and coordinate ownership with the team.
2. Create a descriptive branch, such as `feature/backend-accounts` or `docs/fabric-network`.
3. Keep changes scoped to the assigned module and follow its technology conventions.
4. Open a pull request against the team’s agreed integration branch, explaining the change and any validation performed.
5. Request review from the relevant module owner and address review feedback before merging.

See [CONTRIBUTING.md](CONTRIBUTING.md) for collaboration guidance.
