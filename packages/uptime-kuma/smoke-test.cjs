// Synthetic, loopback-only checks; the temporary account and database are deleted.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const net = require('node:net');
const { spawn } = require('node:child_process');
const { createRequire } = require('node:module');
const root = path.resolve(process.argv[2]);
const appRequire = createRequire(path.join(root, 'package.json'));
const { io } = appRequire('socket.io-client');
const sqlite = appRequire('@louislam/sqlite3');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'uptime-kuma-ci-'));
const data = path.join(temporary, 'data');
const password = 'Synthetic-Only-Local-Test-42!';
const android = process.platform === 'android';
let child, client, monitorID, tcpMonitorID, log = '', requests = 0, tcpConnections = 0, healthy = true;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const target = http.createServer((req, res) => {
    requests++;
    res.writeHead(healthy ? 200 : 503, { 'Content-Type': 'text/plain' });
    res.end('synthetic localhost monitoring fixture');
});
const tcpTarget = net.createServer(socket => { tcpConnections++; socket.end(); });
const listen = server => new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
async function unusedPort() {
    const s = http.createServer(); await listen(s);
    const port = s.address().port;
    await new Promise(resolve => s.close(resolve)); return port;
}
async function waitFor(fn, label, timeout = 60000) {
    const end = Date.now() + timeout;
    let failure;
    while (Date.now() < end) {
        if (child && child.exitCode !== null) throw Error('Server exited: ' + child.exitCode);
        try { const result = await fn(); if (result) return result; } catch (e) { failure = e; }
        await pause(250);
    }
    throw Error('Timed out: ' + label + ': ' + (failure || ''));
}
const ack = (event, ...args) => new Promise((resolve, reject) => {
    client.timeout(20000).emit(event, ...args, (error, result) => {
        if (error) return reject(error);
        if (result && result.ok === false) return reject(Error(event + ': ' + result.msg));
        resolve(result);
    });
});
async function start(port) {
    const env = { ...process.env, DATA_DIR: data, UPTIME_KUMA_HOST: '127.0.0.1',
        UPTIME_KUMA_PORT: String(port), UPTIME_KUMA_DB_TYPE: 'sqlite',
        UPTIME_KUMA_CHECK_UPDATE: '0', NODE_ENV: 'production' };
    const command = process.env.UPTIME_KUMA_TEST_ROOT ? process.execPath : 'uptime-kuma';
    const args = process.env.UPTIME_KUMA_TEST_ROOT ? ['server/server.js'] : [];
    child = spawn(command, args, { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] });
    child.stdout.on('data', chunk => log += chunk.toString());
    child.stderr.on('data', chunk => log += chunk.toString());
    child.on('error', error => log += error.toString());
    const base = 'http://127.0.0.1:' + port;
    const html = await waitFor(async () => {
        const r = await fetch(base + '/dashboard');
        if (!r.ok) return false;
        const body = await r.text(); return body.includes('Uptime Kuma') && body;
    }, 'dashboard');
    const asset = html.match(/src="([^\"]+\.js)"/);
    assert(asset, 'dashboard has built JavaScript');
    const response = await fetch(base + asset[1]);
    assert.equal(response.status, 200);
    assert((await response.arrayBuffer()).byteLength > 10000, 'real dashboard asset');
    client = io(base, { transports: ['websocket'], reconnection: false });
    // The connection callback awaits sendInfo before registering handlers.
    // loginRequired is emitted only after every request handler is ready.
    await new Promise((resolve, reject) => {
        client.once('loginRequired', resolve); client.once('connect_error', reject);
        setTimeout(() => reject(Error('Socket API not ready')), 20000).unref();
    });
}
async function stop() {
    if (client) { client.close(); client = null; }
    if (child && child.exitCode === null) {
        const ended = new Promise(resolve => child.once('exit', resolve));
        child.kill('SIGTERM');
        await Promise.race([ended, pause(20000)]);
        if (child.exitCode === null) { child.kill('SIGKILL'); await ended; throw Error('Unclean shutdown'); }
        assert.equal(child.exitCode, 0, 'graceful stop');
    }
    child = null;
}
async function databaseCheck() {
    const db = new sqlite.Database(path.join(data, 'kuma.db'), sqlite.OPEN_READONLY);
    const rows = await new Promise((resolve, reject) => db.all('SELECT id, name, url FROM monitor', (e, r) => e ? reject(e) : resolve(r)));
    assert(rows.some(row => row.id === monitorID && row.name === 'Synthetic HTTP monitor'));
    assert(rows.some(row => row.id === tcpMonitorID && row.name === 'Synthetic TCP monitor'));
    assert.equal(rows.length, 2, 'unsupported browser monitor was not stored');
    const users = await new Promise((resolve, reject) => db.all('SELECT username, password FROM user', (e, r) => e ? reject(e) : resolve(r)));
    assert.equal(users.length, 1); assert.equal(users[0].username, 'termux-ci');
    assert.notEqual(users[0].password, password);
    await new Promise((resolve, reject) => db.close(e => e ? reject(e) : resolve()));
}
async function main() {
    await listen(target);
    await listen(tcpTarget);
    const port = await unusedPort();
    await start(port);
    assert.equal(await ack('needSetup'), true);
    await ack('setup', 'termux-ci', password);
    await ack('login', { username: 'termux-ci', password, token: '' });
    const beats = [];
    client.on('heartbeat', beat => beats.push(beat));
    const monitor = { type: 'http', name: 'Synthetic HTTP monitor',
        url: 'http://127.0.0.1:' + target.address().port + '/health',
        method: 'GET', interval: 1, retryInterval: 1, resendInterval: 0,
        maxretries: 0, timeout: 5, maxredirects: 0, active: true,
        accepted_statuscodes: ['200-299'], notificationIDList: {},
        upsideDown: false, expiryNotification: false, ignoreTls: false,
        kafkaProducerBrokers: [], kafkaProducerSaslOptions: {}, conditions: [], rabbitmqNodes: [] };
    if (android) {
        const unsupported = /Browser monitors are not supported on Android/;
        await assert.rejects(ack('add', { ...monitor, type: 'real-browser', name: 'Unsupported browser fixture' }), unsupported);
        await assert.rejects(ack('testChrome', '#playwright_chromium'), unsupported);
        await assert.rejects(ack('testRemoteBrowser', { url: 'ws://127.0.0.1:1' }), unsupported);
    }
    const added = await ack('add', monitor);
    monitorID = added.monitorID;
    await waitFor(() => beats.some(b => b.monitorID === monitorID && b.status === 1), 'UP heartbeat');
    healthy = false;
    await waitFor(() => beats.some(b => b.monitorID === monitorID && b.status === 0), 'DOWN heartbeat');
    healthy = true;
    const before = beats.length;
    await waitFor(() => beats.slice(before).some(b => b.monitorID === monitorID && b.status === 1), 'recovery heartbeat');
    assert(requests >= 3);
    const tcpAdded = await ack('add', { ...monitor, type: 'port', name: 'Synthetic TCP monitor',
        hostname: '127.0.0.1', port: tcpTarget.address().port });
    tcpMonitorID = tcpAdded.monitorID;
    await waitFor(() => beats.some(b => b.monitorID === tcpMonitorID && b.status === 1), 'TCP UP heartbeat');
    assert(tcpConnections > 0, 'TCP monitor connected to loopback fixture');
    await stop(); await databaseCheck();
    const connectionsBeforeRestart = tcpConnections;
    await start(port);
    assert.equal(await ack('needSetup'), false);
    await ack('login', { username: 'termux-ci', password, token: '' });
    const result = await ack('getMonitor', monitorID);
    assert.equal(result.monitor.name, 'Synthetic HTTP monitor');
    const tcpResult = await ack('getMonitor', tcpMonitorID);
    assert.equal(tcpResult.monitor.name, 'Synthetic TCP monitor');
    const initialRequests = requests;
    await waitFor(() => requests > initialRequests, 'monitor resumes after restart');
    await waitFor(() => tcpConnections > connectionsBeforeRestart, 'TCP monitor resumes after restart');
    await stop(); await databaseCheck();
    console.log('PASS: Uptime Kuma dashboard/assets, native SQLite, synthetic account login, HTTP UP/DOWN/recovery, TCP connectivity, persisted monitor/account and restart' + (android ? ', unsupported Android browser requests' : ''));
}
main().catch(error => { console.error(error.stack); console.error(log.slice(-20000)); process.exitCode = 1; }).finally(async () => {
    try { await stop(); } catch (e) { console.error(e); process.exitCode = 1; }
    target.closeAllConnections(); await new Promise(resolve => target.close(resolve));
    await new Promise(resolve => tcpTarget.close(resolve));
    fs.rmSync(temporary, { recursive: true, force: true });
});
