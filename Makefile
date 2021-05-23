PREFIX ?= /usr/local
VERSION = "v0.0.1"
SDB ?= $(HOME)/Music/_Serato_/database V2

#all: install
all: build

install:
	# mkdir -p $(DESTDIR)$(PREFIX)/bin
	# install -m 0755 onya-dj-notebook-wrapper $(DESTDIR)$(PREFIX)/bin/onya-dj-notebook

uninstall:
	# @$(RM) $(DESTDIR)$(PREFIX)/bin/onya-dj-notebook
	@docker rmi uogbuji/onya-dj-notebook:$(VERSION)
	@docker rmi uogbuji/onya-dj-notebook:latest

build:
	# @docker build -t uogbuji/onya-dj-notebook:$(VERSION) . \
	# && docker tag uogbuji/onya-dj-notebook:$(VERSION) uogbuji/onya-dj-notebook:latest
	@docker-compose build

publish: build
	@docker push uogbuji/onya-dj-notebook:$(VERSION) \
	&& docker push uogbuji/onya-dj-notebook:latest

run:
	@echo "Expecting Serato DB at" $(SDB)
    # Use --rm? https://docs.docker.com/engine/reference/run/#clean-up---rm
	@docker run -p 8888:8888 --name onya-dj-notebook \
	--mount type=bind,source="$(SDB)",target=/sdb,readonly \
	uogbuji/onya-dj-notebook:$(VERSION)

stop:
	@docker stop onya-dj-notebook \
	&& docker rm onya-dj-notebook

.PHONY: all install uninstall build publish run stop
