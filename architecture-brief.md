# eCommerce Order Processing System - Architecture Brief

## Overview
A cloud-native, serverless order processing pipeline designed for scalability, cost-efficiency, and resilience using AWS services.

## Architecture Diagram
```
[Customer] --> [API Gateway] --> [Lambda: Order Ingest] --> [DynamoDB: Orders Table]
                                         |
                                         v
                                   [SQS: Order Queue]
                                         |
                                         v
                              [Lambda: Order Processor] --> [CloudWatch Logs/Metrics]
                                         |
                                         v
                                [DynamoDB: Update Status]

[Customer] --> [API Gateway] --> [Lambda: Chatbot] --> [Bedrock: GenAI] --> [DynamoDB: Query]
```

## User Flow

### Order Submission Flow
1. **Customer Places Order**
   - Customer submits order via web/mobile app
   - Request hits API Gateway endpoint: `POST /orders`
   - API Gateway validates API key and applies rate limiting

2. **Order Ingestion**
   - API Gateway triggers Order Ingestion Lambda function
   - Lambda validates order data (required fields, business rules)
   - Generates unique order ID and timestamp
   - Stores order in DynamoDB with status "PENDING"
   - Sends order message to SQS queue for async processing
   - Returns order confirmation to customer (201 response)

3. **Asynchronous Order Processing**
   - SQS triggers Order Processing Lambda function
   - Lambda retrieves order from DynamoDB
   - Processes order through business logic pipeline:
     - Order validation
     - Inventory availability check
     - Payment processing simulation
     - Order fulfillment preparation
   - Updates order status in DynamoDB at each step
   - Sends metrics to CloudWatch for monitoring

4. **Order Status Updates**
   - Order progresses through statuses: `PENDING` → `VALIDATING` → `INVENTORY_CHECK` → `PAYMENT_PROCESSING` → `FULFILLMENT` → `COMPLETED`
   - Failed orders marked as `FAILED` with error details
   - All status changes logged to CloudWatch

### Order Status Query Flow
1. **Customer Checks Order Status**
   - Customer makes API call: `GET /orders/{orderId}`
   - API Gateway validates API key and routes request
   - Order Ingestion Lambda queries DynamoDB
   - Returns current order status and details
   - Response includes order history and tracking information

### GenAI Chatbot Flow
1. **Customer Asks Natural Language Question**
   - Customer submits query: `POST /chatbot`
   - Examples: "What's my order status?", "Where is my package?", "Show recent orders"

2. **Query Processing**
   - Chatbot Lambda extracts order/customer IDs from query
   - Queries DynamoDB for relevant order data
   - Constructs context for AI model

3. **AI Response Generation**
   - Calls Amazon Bedrock with customer query and order context
   - Bedrock (Claude model) generates natural language response
   - Fallback to template responses if AI unavailable
   - Returns conversational response to customer

### Error Handling Flow
1. **Processing Failures**
   - Failed messages sent to Dead Letter Queue (DLQ)
   - CloudWatch alarms trigger on error thresholds
   - Lambda functions implement retry logic with exponential backoff
   - Failed orders marked with detailed error messages

2. **System Monitoring**
   - CloudWatch tracks custom metrics (orders/hour, success rates)
   - Lambda execution logs centralized for debugging
   - API Gateway logs all requests for audit trail

## Service Selection & Flow

### 1. API Gateway
- **Purpose**: Public-facing REST API endpoint for order submission and status queries
- **Why**: Managed service with built-in throttling, caching, and security features
- **Features**: Rate limiting, API keys, CORS support, request/response transformation

### 2. AWS Lambda
- **Order Ingestion Function**: Validates orders, generates IDs, stores in DynamoDB
- **Order Processing Function**: Handles business logic, inventory checks, payment processing
- **Chatbot Function**: Processes natural language queries for order status
- **Why**: Serverless, auto-scaling, pay-per-use model reduces costs

### 3. Amazon DynamoDB
- **Orders Table**: Primary storage for order data
- **Schema**: Partition key (orderId), sort key (timestamp), GSI on customerId
- **Why**: NoSQL, auto-scaling, single-digit millisecond latency, cost-effective

### 4. Amazon SQS
- **Order Processing Queue**: Decouples ingestion from processing
- **Dead Letter Queue**: Handles failed processing attempts
- **Why**: Fully managed, reliable message delivery, handles traffic spikes

### 5. Amazon CloudWatch
- **Logs**: Centralized logging for all Lambda functions
- **Metrics**: Custom business metrics and AWS service metrics
- **Alarms**: Automated alerts for error rates, latency thresholds
- **Why**: Built-in observability with AWS services integration

### 6. Amazon Bedrock (Bonus)
- **GenAI Model**: Claude/Titan for natural language order status queries
- **Why**: Managed AI service, no infrastructure management required

## Security Considerations

### Authentication & Authorization
- API Gateway with API keys for external clients
- IAM roles with least privilege principle for Lambda functions
- Resource-based policies for DynamoDB access

### Data Protection
- Encryption in transit (TLS 1.2+) via API Gateway
- Encryption at rest for DynamoDB
- VPC endpoints for internal service communication
- Secrets Manager for sensitive configuration

### Network Security
- API Gateway in public subnet with WAF protection
- Lambda functions in private subnets
- Security groups restricting unnecessary traffic
- VPC Flow Logs for network monitoring

## Scalability Considerations

### Horizontal Scaling
- **Lambda**: Auto-scales to handle concurrent requests (up to 1000 concurrent executions)
- **DynamoDB**: On-demand scaling based on traffic patterns
- **SQS**: Scales to handle millions of messages
- **API Gateway**: Handles 10,000 requests per second by default

### Performance Optimization
- **DynamoDB**: Global Secondary Indexes for efficient queries
- **Lambda**: Reserved concurrency for critical functions
- **API Gateway**: Response caching for frequent queries
- **CloudWatch**: Custom metrics for proactive scaling decisions

### Cost Optimization
- **Lambda**: Pay only for execution time
- **DynamoDB**: On-demand pricing for variable workloads
- **SQS**: Pay per message, no minimum fees
- **API Gateway**: Pay per API call with caching to reduce backend calls

## Resilience & Reliability

### Fault Tolerance
- Multi-AZ deployment for all managed services
- Dead letter queues for failed message processing
- Lambda retry mechanisms with exponential backoff
- Circuit breaker pattern implementation

### Disaster Recovery
- DynamoDB cross-region replication available
- Lambda functions deployed via Infrastructure as Code
- Automated backup and restore procedures
- RPO: < 1 hour, RTO: < 30 minutes

## Development & Operations

### CI/CD Pipeline
- Infrastructure as Code using AWS CDK/CloudFormation
- Automated testing and deployment via GitHub Actions
- Environment promotion (dev -> staging -> prod)
- Blue/green deployment for zero-downtime updates

### Monitoring & Alerting
- Custom CloudWatch dashboards
- Automated alerting for error rates > 1%
- Performance monitoring for latency > 3 seconds
- Business metrics tracking (orders/hour, revenue)

## Trade-offs Made

1. **Eventual Consistency**: Chose DynamoDB for scalability over ACID compliance
2. **Cold Start Latency**: Lambda functions may have initial latency but provide cost benefits
3. **NoSQL Schema**: Flexible schema vs. relational data integrity
4. **Serverless**: Vendor lock-in vs. operational simplicity

## Production Evolution Path

### Phase 1: MVP (Current POC)
- Basic order ingestion and processing
- Simple status queries
- Basic monitoring

### Phase 2: Enhanced Features
- Advanced inventory management
- Payment processing integration
- Real-time notifications via SNS/SES
- Enhanced chatbot capabilities

### Phase 3: Enterprise Scale
- Multi-region deployment
- Advanced analytics with Kinesis/Athena
- Machine learning for demand forecasting
- GraphQL API for frontend optimization

## Cost Estimation (Monthly)
- API Gateway: ~$3.50 per million requests
- Lambda: ~$0.20 per million requests
- DynamoDB: ~$1.25 per million reads/writes
- SQS: ~$0.40 per million requests
- CloudWatch: ~$0.50 per GB of logs

**Estimated monthly cost for 1M orders: ~$50-100**