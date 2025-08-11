import boto3

s3 = boto3.resource('s3')

# Get list of objects for indexing
images=[('rajiv.jpg','Rajiv Upadhyay'),
      ('vishal.jpg','Vishal Dubey'),
      ('ankita.jpg','Ankita Upadhyay'),
      ('NeelamPhadnis.jpg','Neelam Phadnis'),
      ('rajeshGaikwad.jpg','Rajesh Gaikwad'),
      ('amitesh.jpg','Amitesh Yadav')
      ]

# Iterate through list to upload objects to S3   
for image in images:
    file = open(image[0],'rb')
    object = s3.Object('famouspersons-facerecognition-123xyz','index/'+ image[0])
    ret = object.put(Body=file,
                    Metadata={'FullName':image[1]})