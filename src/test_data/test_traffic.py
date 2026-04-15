from traffic_generator import generate_zipf_requests

requests = generate_zipf_requests(10)

for r in requests:
    print(r)