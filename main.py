import boto3
import os
import sys
from botocore.exceptions import ClientError
import argparse

class FaceRecognitionSystem:
    def __init__(self, bucket_name=None, table_name=None):
        """Initialize the face recognition system with AWS services."""
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.client('dynamodb')
        self.rekognition = boto3.client('rekognition')
        
        # Get bucket and table names from environment or parameters
        self.bucket_name = bucket_name or os.getenv('FACE_RECOGNITION_BUCKET')
        self.table_name = table_name or os.getenv('FACE_RECOGNITION_TABLE') or 'facerecognition'
        self.collection_id = 'facerecognition_collection'
        
        if not self.bucket_name:
            raise ValueError("Bucket name must be provided either as parameter or environment variable")

    def upload_face(self, image_path, full_name):
        """Upload an image with metadata to S3."""
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Extract filename from path
            filename = os.path.basename(image_path)
            
            print(f"Uploading {filename} for {full_name}...")
            
            # Upload to S3 with metadata
            with open(image_path, 'rb') as image:
                self.s3.upload_fileobj(
                    image,
                    self.bucket_name,
                    filename,
                    ExtraArgs={
                        'Metadata': {'fullname': full_name}
                    }
                )
            
            print(f"Successfully uploaded {filename}")
            return True
            
        except ClientError as e:
            print(f"Error uploading image: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return False

    def list_faces(self):
        """List all faces stored in DynamoDB."""
        try:
            response = self.dynamodb.scan(
                TableName=self.table_name
            )
            
            if 'Items' in response:
                print("\nRecognized Faces:")
                print("-----------------")
                for item in response['Items']:
                    print(f"Name: {item['FullName']['S']}")
                    print(f"Face ID: {item['RekognitionId']['S']}")
                    print("-----------------")
                return response['Items']
            else:
                print("No faces found in the database.")
                return []
                
        except ClientError as e:
            print(f"Error listing faces: {str(e)}")
            return None

    def delete_face(self, face_id):
        """Delete a face from both Rekognition collection and DynamoDB."""
        try:
            # Delete from Rekognition collection
            self.rekognition.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=[face_id]
            )
            
            # Delete from DynamoDB
            self.dynamodb.delete_item(
                TableName=self.table_name,
                Key={'RekognitionId': {'S': face_id}}
            )
            
            print(f"Successfully deleted face with ID: {face_id}")
            return True
            
        except ClientError as e:
            print(f"Error deleting face: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Face Recognition System CLI')
    parser.add_argument('--bucket', help='S3 bucket name')
    parser.add_argument('--table', help='DynamoDB table name')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a face image')
    upload_parser.add_argument('image_path', help='Path to the image file')
    upload_parser.add_argument('full_name', help='Full name of the person')
    
    # List command
    subparsers.add_parser('list', help='List all recognized faces')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a face')
    delete_parser.add_argument('face_id', help='Face ID to delete')
    
    args = parser.parse_args()
    
    try:
        system = FaceRecognitionSystem(args.bucket, args.table)
        
        if args.command == 'upload':
            system.upload_face(args.image_path, args.full_name)
        elif args.command == 'list':
            system.list_faces()
        elif args.command == 'delete':
            system.delete_face(args.face_id)
        else:
            parser.print_help()
            
    except ValueError as e:
        print(f"Configuration error: {str(e)}")
        print("\nPlease provide bucket and table names either as arguments or environment variables:")
        print("  --bucket BUCKET_NAME")
        print("  --table TABLE_NAME")
        print("\nOr set environment variables:")
        print("  FACE_RECOGNITION_BUCKET")
        print("  FACE_RECOGNITION_TABLE")
        sys.exit(1)

if __name__ == "__main__":
    main() 