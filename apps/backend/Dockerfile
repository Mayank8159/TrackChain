# ---- Stage 1: build deps ----
FROM public.ecr.aws/lambda/python:3.10 AS build

RUN yum install -y gcc gcc-c++ make cmake git && \
    yum clean all

COPY requirements.txt /build/
RUN pip install --no-cache-dir --target /build/layer/python -r /build/requirements.txt

# ---- Stage 2: runtime ----
FROM public.ecr.aws/lambda/python:3.10

# OpenCV headless needs these libs at runtime
RUN yum install -y mesa-libGL glib2 && \
    yum clean all

COPY --from=build /build/layer/python ${LAMBDA_TASK_ROOT}/
COPY main.py ${LAMBDA_TASK_ROOT}/

CMD ["main.handler"]
