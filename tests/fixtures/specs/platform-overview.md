# Platform Modernization

## Vision

Migrate the monolithic application to a modular architecture that enables
independent team deployment, horizontal scaling, and faster iteration
cycles. Target state: fully containerized services behind an API gateway
with shared observability infrastructure.

## Architecture

Three-tier architecture: API gateway, service mesh, and data layer. Each
bounded context becomes an independent service with its own data store.
Inter-service communication uses async messaging for writes and synchronous
gRPC for reads.

## Technology decisions

- **Runtime**: Node.js 20 LTS for API services, Python 3.12 for ML pipeline.
- **Orchestration**: Kubernetes on EKS with Helm charts per service.
- **Messaging**: Apache Kafka for event streaming between services.
- **Observability**: OpenTelemetry SDK with Grafana stack for dashboards.

## Feature map

- Authentication and authorization (OAuth 2.1 + RBAC)
- User management and profile service
- Dashboard and analytics engine
- Notification service (email, push, in-app)
- Search and indexing pipeline
- Billing and subscription management

## Cross-cutting concerns

- **Security**: mTLS between services, secrets in Vault, SAST in CI.
- **Reliability**: circuit breakers, retry budgets, chaos testing quarterly.
- **Compliance**: GDPR data residency, SOC 2 audit trail on all mutations.

## Open questions

- Should we adopt a service mesh (Istio) or handle routing at the app level?
  Istio adds operational complexity but gives us mTLS and traffic shaping
  for free.
