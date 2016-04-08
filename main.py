"""
A receiver for https://github.com/gaker/snmp-send
or any application to send data to InfluxDB.
"""
import aiohttp
import asyncio
import os

from aiohttp import web
from influxdb import line_protocol


async def ping(request):
    """
    Used for service health checks
    """
    return web.json_response({'ping': 'pong'})


async def save(data, db_name=None):
    """
    Save data into influx.
    """
    if not db_name:
        db_name = os.getenv('INFLUX_DB_NAME', 'monitor')

    url = os.getenv('INFLUXDB_PORT_8086_TCP', '')
    if url == '':
        raise Exception('INFLUXDB_PORT_8086_TCP is required in the env!')

    url = '{}/write?db={}'.format(
        url, db_name)

    auth = aiohttp.BasicAuth(
        os.getenv('INFLUX_USER', 'root'),
        password=os.getenv('INFLUX_PASS', 'root')
    )

    return await aiohttp.post(url, data=data, auth=auth)


async def receive(request):
    """
    Receive data and drop it in InfluxDB.
    """
    data = await request.json()

    auth_header = request.headers.get('authorization')
    if auth_header:
        auth_parts = auth_header.split(' ')

        token = os.getenv('AUTH_TOKEN', None)
        if token:
            if token != auth_parts[1]:
                return web.Response(status=401)

    if 'data' in data.keys():
        db = data.get('db', None)
        for item in data.get('data'):
            lines = line_protocol.make_lines(item)
            resp = await save(lines, db_name=db)
            resp.close()
        return web.Response(status=201)

    points = data.get('points')
    if points:
        # convert ints to floats
        for idx, item in enumerate(points):
            fields = item.get('fields')
            if fields:
                for k, v in fields.items():
                    if k != 'time':
                        if isinstance(v, int):
                            data['points'][idx]['fields'][k] = float(v)

        lines = line_protocol.make_lines(data)
        resp = await save(lines)
        resp.close()
    return web.Response(status=201)


def main():

    app = web.Application()
    app.router.add_route('GET', '/ping', ping)
    app.router.add_route('POST', '/receive', receive)

    loop = asyncio.get_event_loop()
    handler = app.make_handler()
    f = loop.create_server(handler, '0.0.0.0', 8000)
    srv = loop.run_until_complete(f)

    print('serving on', srv.sockets[0].getsockname())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()
        loop.run_until_complete(srv.wait_closed())
        loop.run_until_complete(handler.finish_connections(1.0))
        loop.run_until_complete(app.finish())
    loop.close()

if __name__ == '__main__':
    main()
