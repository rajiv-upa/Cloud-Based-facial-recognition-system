# Face Recognition System

This project implements a face recognition system using AWS services including S3, Lambda, DynamoDB, and Amazon Rekognition.

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI installed and configured
3. Python 3.9 or later

## Infrastructure Setup

1.-- install aws shell 
--aws configure
 --Create an Amazon Rekognition Collection:
   ```bash
   aws rekognition create-collection --collection-id facerecognition 
   ```

2. Deploy the CloudFormation template:
   ```bash
   aws cloudformation create-stack \
     --stack-name face-recognition-stack \
     --template-body file://cloudformation.yml \
     --capabilities CAPABILITY_IAM
     --Create table on DynamoDB
     --create S3 bucket and name it 

   ```
3. Create  IAM Role with necessary permissions

4. Wait for the stack to be created (this may take a few minutes)

## Usage

1. Upload an image to the S3 bucket with metadata:
   ```bash
   aws s3 cp your-image.jpg s3://face-recognition-images-<your-account-id>/your-image.jpg \
     --metadata fullname="Person Name"
   ```

2. The Lambda function will automatically:
   - Detect faces in the uploaded image
   - Index the face in the Rekognition collection
   - Store the face ID and person's name in DynamoDB

## Important Notes

### Image Requirements
- Use clear, well-lit images
- Each image should contain exactly one face
- Supported formats: JPEG, PNG
- Image size should be reasonable (recommended: under 5MB)

### Metadata Requirements
- The `fullname` metadata field is required
- Example: `--metadata fullname="John Doe"`

### Error Handling
The system will return appropriate error messages for:
- Missing face in the image
- Multiple faces detected
- Missing required metadata
- Invalid image format
- Processing errors

## Resources Created

- S3 Bucket: `face-recognition-images-<account-id>`
- DynamoDB Table: `face-recognition-table`
- Lambda Function: `face-recognition-function`
- IAM Role with necessary permissions
- S3 Event Notifications
- CloudWatch Log Group for Lambda function

## Monitoring and Debugging

1. View Lambda function logs:
   ```bash
   aws logs get-log-events \
     --log-group-name /aws/lambda/face-recognition-function \
     --log-stream-name <latest-log-stream>
   ```

2. Check DynamoDB records:
   ```bash
   aws dynamodb scan --table-name face-recognition-table
   ```

## Cleanup

To remove all created resources:

1. Delete the Rekognition collection:
   ```bash
   aws rekognition delete-collection --collection-id famouspersons
   ```

2. Delete the CloudFormation stack:
   ```bash
   aws cloudformation delete-stack --stack-name face-recognition-stack
   ```

3. Delete the CloudWatch log group:
   ```bash
   aws logs delete-log-group --log-group-name /aws/lambda/face-recognition-function
   ```

## Security Notes

- All resources are created with minimal required permissions
- S3 bucket is private and blocks public access
- Lambda function has specific IAM permissions for required services
- CloudWatch logs are enabled for monitoring and debugging 