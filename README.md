# Drycc Helmbroker

[![Build Status](https://drone.drycc.cc/api/badges/drycc/helmbroker/status.svg)](https://drone.drycc.cc/drycc/helmbroker)
[![codecov.io](https://codecov.io/github/drycc/helmbroker/coverage.svg?branch=main)](https://codecov.io/github/drycc/helmbroker?branch=main)

Drycc (pronounced DAY-iss) Workflow is an open source Platform as a Service (PaaS) that adds a developer-friendly layer to any [Kubernetes](http://kubernetes.io) cluster, making it easy to deploy and manage applications on your own servers.

For more information about the Drycc Workflow, please visit the main project page at https://github.com/drycc/workflow.

We welcome your input! If you have feedback, please [submit an issue][issues]. If you'd like to participate in development, please read the "Development" section below and [submit a pull request][prs].

# About

Helm Broker is a [Service Broker](https://github.com/openservicebrokerapi/servicebroker) that exposes Helm charts as Service Classes in [Service Catalog](https://svc-cat.io/). To do so, Helm Broker uses the concept of addons. An addon is an abstraction layer over a Helm chart which provides all information required to convert the chart into a Service Class.

You can install Helm Broker either as a standalone project, or as part of [Drycc workflow](https://www.drycc.cc/). 

To see all addons that Helm Broker provides, go to the [`addons`](https://github.com/drycc/addons) repository.

Helm Broker implements the [Open Service Broker API](https://github.com/openservicebrokerapi/servicebroker/blob/v2.14/profile.md#service-metadata) (OSB API). To be compliant with Service Catalog version used in drycc workflow.

# Development

The Drycc project welcomes contributions from all developers. The high-level process for development matches many other open source projects. See below for an outline.

* Fork this repository
* Make your changes
* [Submit a pull request][prs] (PR) to this repository with your changes, and unit tests whenever possible.
* Drycc project maintainers will review your code.
* After two maintainers approve it, they will merge your PR.
