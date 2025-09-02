import json
import boto3
import uuid
import os
from datetime import datetime
from decimal import Decimal
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
sns = boto3.client('sns')

# Environment variables
ORDERS_TABLE_NAME = os.environ['ORDERS_TABLE_NAME']
ORDER_QUEUE_URL = os.environ['ORDER_QUEUE_URL']
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

def handler(event, context):
    """
    Lambda function to handle order ingestion and retrieval
    """
    try:
        http_method = event['httpMethod']
        
        if http_method == 'POST':
            return create_order(event, context)
        elif http_method == 'GET':
            return get_order(event, context)
        else:
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Method not allowed'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

def create_order(event, context):
    """
    Create a new order
    """
    try:
        # Parse request body
        body = json.loads(event['body'])
        
        # Validate required fields
        required_fields = ['customerId', 'items', 'totalAmount']
        for field in required_fields:
            if field not in body:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': f'Missing required field: {field}'}),
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    }
                }
        
        # Generate order ID and timestamp
        order_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Prepare order data
        order_data = {
            'orderId': order_id,
            'timestamp': timestamp,
            'customerId': body['customerId'],
            'items': body['items'],
            'totalAmount': Decimal(str(body['totalAmount'])),
            'status': 'PENDING',
            'createdAt': timestamp,
            'updatedAt': timestamp
        }
        
        # Add optional fields
        if 'customerEmail' in body:
            order_data['customerEmail'] = body['customerEmail']
        if 'shippingAddress' in body:
            order_data['shippingAddress'] = body['shippingAddress']
        if 'billingAddress' in body:
            order_data['billingAddress'] = body['billingAddress']
        
        # Save to DynamoDB
        table = dynamodb.Table(ORDERS_TABLE_NAME)
        table.put_item(Item=order_data)
        
        # Send message to SQS for processing
        message_body = {
            'orderId': order_id,
            'action': 'PROCESS_ORDER',
            'timestamp': timestamp
        }
        
        sqs.send_message(
            QueueUrl=ORDER_QUEUE_URL,
            MessageBody=json.dumps(message_body),
            MessageGroupId=order_id if ORDER_QUEUE_URL.endswith('.fifo') else None
        )
        
        logger.info(f"Order {order_id} created successfully")
        
        # Send SMS notification for order creation
        send_order_notification(order_id, 'CREATED', order_data)
        
        # Return success response
        response_data = {
            'orderId': order_id,
            'status': 'PENDING',
            'message': 'Order created successfully',
            'timestamp': timestamp
        }
        
        return {
            'statusCode': 201,
            'body': json.dumps(response_data, default=str),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to create order'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

def get_order(event, context):
    """
    Retrieve order by ID
    """
    try:
        # Extract order ID from path parameters
        order_id = event['pathParameters']['orderId']
        
        if not order_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Order ID is required'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # Query DynamoDB
        table = dynamodb.Table(ORDERS_TABLE_NAME)
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('orderId').eq(order_id)
        )
        
        if not response['Items']:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Order not found'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # Get the most recent order record (sorted by timestamp)
        order = response['Items'][0]
        
        logger.info(f"Order {order_id} retrieved successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps(order, default=str),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving order: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to retrieve order'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

def send_order_notification(order_id, event_type, order_data=None):
    """
    Send SMS notification for order events
    """
    if not SNS_TOPIC_ARN:
        logger.warning("SNS_TOPIC_ARN not configured, skipping SMS notification")
        return
    
    try:
        if event_type == 'CREATED':
            total_amount = order_data.get('totalAmount', 'Unknown')
            customer_id = order_data.get('customerId', 'Unknown')
            item_count = len(order_data.get('items', []))
            
            message = f"🛒 Order Created!\n"
            message += f"Order ID: {order_id[:8]}...\n"
            message += f"Customer: {customer_id}\n"
            message += f"Items: {item_count}\n"
            message += f"Total: €{total_amount}\n"
            message += f"Status: Processing\n"
            message += f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
        else:
            message = f"Order {order_id[:8]}... - {event_type}"
        
        # Send SMS via SNS
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject=f"eCommerce Order {event_type}"
        )
        
        logger.info(f"SMS notification sent for order {order_id} - {event_type}")
        
    except Exception as e:
        logger.error(f"Failed to send SMS notification: {str(e)}")
        # Don't fail the main process if notification fails