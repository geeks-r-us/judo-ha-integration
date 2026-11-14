# Judo Postman Guide

This project uses two HTTP interfaces you can test directly in Postman:

- Local device REST: `http://<host>:<port>/api/rest/...`
- Judo cloud interface: `https://www.myjudo.eu/interface`

## Cloud Authentication

The integration logs in with a `GET` request to:

- `https://www.myjudo.eu/interface`

Query parameters:

- `group=register`
- `command=login`
- `name=login`
- `user=<your app username>`
- `password=<MD5 hex of your plain-text password>`
- `nohash=Service`
- `role=customer`

The response includes a `token`. Reuse that token in later cloud requests.

## Cloud Read

Read cloud device data with:

- `group=register`
- `command=get device data`
- `token=<token>`

The response usually contains device identifiers such as:

- `sn`
- `serialnumber`
- optional `ewuid`

Use those values for writes.

## Cloud Write

Write one command with:

- `group=register`
- `command=set device data`
- `token=<token>`
- `cmd=<command token>`
- `data=<hex payload>`

Optional target parameters:

- `sn=<sn>`
- `serialnumber=<serialnumber>`
- `ewuid=<ewuid>`

### Target Hardness

For target hardness (`0x30`), this integration now uses:

- `cmd=3000`
- `data=<hex payload>`

Examples:

- `7 dH` -> `data=07`
- `10 dH` -> `data=0A`
- 2-byte compatibility form -> `data=0A00`

## Local REST

Local read:

- `GET http://<host>:<port>/api/rest/<CMD>00`

Local write:

- `GET http://<host>:<port>/api/rest/<CMD>00<PAYLOAD>`

Examples:

- Read target hardness: `/api/rest/5100`
- Write target hardness `10 dH`: `/api/rest/30000A00`

## Included Files

- Postman collection: [Judo.postman_collection.json](/workspaces/judo-ha-integration/docs/postman/Judo.postman_collection.json)
- Postman environment template: [Judo.postman_environment.json](/workspaces/judo-ha-integration/docs/postman/Judo.postman_environment.json)

Import both into Postman, fill the environment variables, run `Cloud Login`, then use the cloud or local requests.
