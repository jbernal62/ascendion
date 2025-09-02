# 🛒 eCommerce Order Processing System

A cloud-native, serverless order processing pipeline built on AWS, designed for scalability, cost-efficiency, and resilience.

## 🎯 Project Overview

This system modernizes legacy order processing for a mid-sized eCommerce company with:
- **Public-facing API** for order ingestion
- **Scalable database** for order storage
- **Asynchronous processing** for business logic
- **Observability** with logging and metrics
- **GenAI chatbot** for order status queries (bonus feature)

## 🏗️ Architecture

```
[Customer] → [API Gateway] → [Lambda: Order Ingest] → [DynamoDB]
                                     ↓
                               [SQS Queue]
                                     ↓
                          [Lambda: Order Processor] → [CloudWatch]
                                     
[Customer] → [API Gateway] → [Lambda: Chatbot] → [Bedrock GenAI]
```

### Key Components

- **Amazon API Gateway**: REST API with authentication and rate limiting
- **AWS Lambda**: Serverless compute for order processing logic
- **Amazon DynamoDB**: NoSQL database with auto-scaling
- **Amazon SQS**: Message queue for asynchronous processing
- **Amazon CloudWatch**: Monitoring, logging, and custom metrics
- **Amazon Bedrock**: GenAI-powered chatbot for customer queries
- **Amazon SNS**: SMS notifications for order events

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Node.js and npm (for AWS CDK)
- Python 3.8+ and pip
- Git

### Deployment

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd ecommerce-order-processing
   chmod +x deploy.sh
   ```

2. **Deploy infrastructure**:
   ```bash
   ./deploy.sh
   ```

3. **Test the system**:
   ```bash
   python demo/test-api.py
   ```

### Manual Deployment

If you prefer manual deployment:

```bash
# Install dependencies
pip install -r requirements.txt
npm install -g aws-cdk

# Bootstrap CDK
cdk bootstrap

# Deploy
cdk deploy

# Get API endpoint and key from outputs
aws cloudformation describe-stacks --stack-name ECommerceOrderProcessingStack
```

## 📡 API Endpoints

### Create Order
```bash
POST /orders
Content-Type: application/json
X-API-Key: <your-api-key>

{
  "customerId": "customer123",
  "items": [
    {
      "productId": "LAPTOP001",
      "name": "Gaming Laptop",
      "quantity": 1,
      "price": 1299.99
    }
  ],
  "totalAmount": 1299.99,
  "customerEmail": "customer@example.com",
  "shippingAddress": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zipCode": "12345",
    "country": "USA"
  }
}
```

### Get Order Status
```bash
GET /orders/{orderId}
X-API-Key: <your-api-key>
```

### Chatbot Query
```bash
POST /chatbot
Content-Type: application/json
X-API-Key: <your-api-key>

{
  "query": "What's the status of my order?",
  "customerId": "customer123"
}
```

## 🔄 User Flow & Order Processing

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
   - SMS notifications sent for order creation, completion, and failures

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

## 🤖 GenAI Chatbot Features

- Natural language order status queries
- Customer order history lookup
- General customer service responses
- Powered by Amazon Bedrock (Claude model)

Example interactions:
- "What's the status of order abc-123-def?"
- "Show me my recent orders"
- "How do I track my package?"

## 📱 SMS Notification System

- **Order Creation**: Instant SMS when order is placed with order details
- **Order Completion**: SMS notification when order is ready for shipping
- **Order Failures**: Alert SMS if order processing fails with reason
- **Phone Number**: +31629408162 (configured in CDK)
- **Message Format**: Includes order ID, customer info, total amount, and timestamp

Example SMS messages:
```
🛒 Order Created!
Order ID: abc12345...
Customer: customer123
Items: 2
Total: €149.99
Status: Processing
Time: 2024-01-15 14:30:25 UTC

✅ Order Completed!
Order ID: abc12345...
Status: Ready for shipping
Completed: 2024-01-15 14:35:42 UTC
```

## 📊 Monitoring & Observability

### CloudWatch Metrics
- Order processing success/failure rates
- API response times and error rates
- Lambda function durations and errors
- DynamoDB read/write capacity metrics

### Custom Business Metrics
- Orders per hour/day
- Average order value
- Processing time by order stage
- Customer satisfaction scores

### Log Aggregation
- Structured logging across all Lambda functions
- Centralized error tracking
- Request/response tracing

## 🔒 Security Features

- **API Authentication**: API keys with usage plans and quotas
- **IAM Roles**: Least privilege access for all services
- **Encryption**: In-transit (TLS) and at-rest encryption
- **Network Security**: VPC security groups and NACLs
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: API Gateway throttling and DDoS protection

## 💰 Cost Optimization

Estimated monthly costs for 1M orders:
- API Gateway: ~$3.50
- Lambda: ~$20
- DynamoDB: ~$25
- SQS: ~$0.40
- SNS: ~$0.75 (SMS messages)
- CloudWatch: ~$5
- **Total: ~$55-105/month**

Cost optimization features:
- On-demand pricing for variable workloads
- Lambda reserved concurrency for cost control
- DynamoDB on-demand scaling
- CloudWatch log retention policies

## 🔧 Configuration

### Environment Variables
- `ORDERS_TABLE_NAME`: DynamoDB table for orders
- `ORDER_QUEUE_URL`: SQS queue for processing
- `BEDROCK_MODEL_ID`: AI model for chatbot
- `SNS_TOPIC_ARN`: SNS topic for SMS notifications

### Infrastructure Parameters
- API throttling limits
- Lambda timeout and memory settings
- DynamoDB read/write capacity modes
- CloudWatch log retention periods

## 🧪 Testing

### Unit Tests
```bash
cd lambda/order_ingestion
python -m pytest tests/
```

### Integration Tests
```bash
python demo/test-api.py
```

### Load Testing
```bash
# Using artillery.js or similar
artillery run load-test-config.yml
```

## 🚀 Production Readiness

### Current POC Status: **Medium Fidelity Prototype**
✅ Working API endpoints  
✅ Async processing pipeline  
✅ GenAI chatbot integration  
✅ Basic observability  
✅ Infrastructure as Code  

### Next Steps for Production:
- [ ] Payment gateway integration
- [ ] Inventory management system
- [ ] Email/SMS notifications
- [ ] Admin dashboard
- [ ] Multi-region deployment
- [ ] Advanced analytics
- [ ] CI/CD pipeline
- [ ] Comprehensive testing suite

## 📈 Scaling Considerations

### Current Capacity
- **API Gateway**: 10,000 RPS
- **Lambda**: 1,000 concurrent executions
- **DynamoDB**: Unlimited (on-demand)
- **SQS**: Unlimited messages

### Scaling Strategies
- Implement caching with ElastiCache
- Add CDN for static content
- Partition data across regions
- Implement database sharding
- Use Lambda provisioned concurrency

## 🛠️ Development

### Local Development
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run local tests
pytest

# Local API testing
sam local start-api
```

### Code Structure
```
├── infrastructure/          # CDK infrastructure code
├── lambda/                 # Lambda function code
│   ├── order_ingestion/    # Order creation and retrieval
│   ├── order_processing/   # Async order processing
│   └── chatbot/           # GenAI chatbot
├── demo/                  # Demo and testing scripts
└── docs/                  # Documentation
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For questions and support:
- Create an issue in this repository
- Contact the development team
- Check the documentation in `/docs`

---

**Built with ❤️ for the AWS Prototyping Challenge**