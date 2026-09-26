// Run with: node --test tests/test_frontend.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function setup() {
    const elements = new Map();
    const element = id => {
        if (!elements.has(id)) elements.set(id, {
            textContent: id, disabled: false,
            classList: { add() {}, remove() {}, toggle() {} },
            addEventListener() {}, setAttribute() {}
        });
        return elements.get(id);
    };
    const context = vm.createContext({
        document: { hidden: true, getElementById: element,
            querySelector: element, addEventListener() {} },
        console, setInterval() {}, setTimeout() {}, clearTimeout() {},
        fetch: async () => { throw new Error('Unexpected request'); }
    });
    vm.runInContext(fs.readFileSync('static/script.js', 'utf8'), context);
    return { context, run: code => vm.runInContext(code, context), element };
}

test('active play polls faster, waiting and finished phases slow down', () => {
    const { run } = setup();
    for (const [status, expected] of [['in_progress', 500], ['betting', 500], ['waiting', 1000], ['finished', 2500]]) {
        assert.equal(run(`currentGame.status = '${status}'; pollDelay()`), expected);
    }
});

test('double clicks send one action and restore controls after failure', async () => {
    const { context, run, element } = setup();
    let reject;
    let count = 0;
    context.action = () => { count++; return new Promise((resolve, fail) => { reject = fail; }); };
    const first = run('runAction(action, hitBtn)');
    assert.equal(element('hitBtn').textContent, 'Working…');
    assert.equal(element('standBtn').disabled, true);
    await run('runAction(action, hitBtn)');
    assert.equal(count, 1);
    reject(new Error('Network failure'));
    await assert.rejects(first);
    assert.equal(run('actionPending'), false);
    assert.equal(element('hitBtn').textContent, 'hitBtn');
});

test('a poll started before an action cannot apply stale state after JSON decoding', async () => {
    const { context, run } = setup();
    let resolveBody;
    context.fetch = async () => ({ ok: true, json: () => new Promise(resolve => { resolveBody = resolve; }) });
    run("document.hidden = false; currentGame.id = 'ABC'; currentGame.status = 'in_progress';");
    const poll = run('pollGameState()');
    await new Promise(resolve => setImmediate(resolve));
    run('actionEpoch += 1');
    resolveBody({ status: 'waiting' });
    await poll;
    assert.equal(run('currentGame.status'), 'in_progress');
    assert.equal(run('pollingGame'), false);
});

test('unchanged snapshots avoid rendering the table again', () => {
    const { run } = setup();
    run('lastRenderedState = JSON.stringify({status: "waiting"});');
    // An attempted render would require players and throw; identical state returns early.
    assert.doesNotThrow(() => run('updateGameUI({status: "waiting"})'));
});
