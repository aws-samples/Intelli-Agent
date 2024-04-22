# Load .env file if it exists
-include .env
export # export all variables defined in .env

env-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	fi

build:
	./local_build.sh

test: env-API_GATEWAY_URL env-API_GATEWAY_URL_TOKEN
	./local_test.sh $(filter-out $@,$(MAKECMDGOALS))

testk: env-API_GATEWAY_URL env-API_GATEWAY_URL_TOKEN
	./local_test_k.sh $(filter-out $@,$(MAKECMDGOALS))

rebuild:
	rm -rf venv
	./local_build.sh