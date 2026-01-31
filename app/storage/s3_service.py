from config.config import s3_client, settings
from botocore.exceptions import ClientError

class S3Service:
    @staticmethod
    def get_file(file_key: str):
        try:
            response = s3_client.get_object(Bucket=settings.BUCKET_NAME, Key=file_key)
            return response['Body'].read()
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return None
            raise e

s3_service = S3Service()