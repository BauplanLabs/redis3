FROM public.ecr.aws/lambda/python:3.10

# install the new, updated boto3 to leverage the new buckets
RUN pip3 install --upgrade pip && pip3 install boto3==1.33.2 --target "${LAMBDA_TASK_ROOT}" && pip3 install redis==5.0.1 --target "${LAMBDA_TASK_ROOT}"

COPY redis3/redis3.py ${LAMBDA_TASK_ROOT}
COPY serverless/app.py ${LAMBDA_TASK_ROOT}

# Set the CMD to the lambda handler
CMD [ "app.lambda_handler" ]