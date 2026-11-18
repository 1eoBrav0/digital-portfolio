const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const test = require('node:test');

const workflow = JSON.parse(readFileSync(join(__dirname, 'fl-orders-n8n.json'), 'utf8'));
const node = workflow.nodes.find(node => node.type === 'n8n-nodes-base.code');
const runCode = new Function('$input', node.parameters.jsCode);

function run(items) {
  return runCode({ all: () => items.map(json => ({ json })) });
}

// Синтетические адреса проверяют формат ссылок. Тест не открывает эти адреса.
function project(suffix) {
  return 'https://www.fl.ru/projects/90000000000000000000000' + suffix + '/';
}

test('отбирает по ссылке и теме, убирает повторы, сортирует и извлекает поля', () => {
  const result = run([
    { title: 'Учебная задача A', description: '<b>Собрать сайт</b>', link: project(1), isoDate: '2025-01-04' },
    { title: 'Учебный сайт (бюджет: 3000, для всех)', link: project(2), isoDate: '2025-01-01' },
    { title: 'Повтор: сайт', link: project(2) + '?test=1' },
    { title: 'Учебный Telegram-бот', description: 'Лендинг', link: project(3), isoDate: '2025-01-03' },
    { title: 'Учебное видео', link: project(4), isoDate: '2025-01-02' },
    { title: 'Учебный сайт на другом домене', link: 'https://example.invalid/projects/1' },
  ]);
  assert.deepEqual(result.map(item => item.pairedItem.item), [1, 3, 4, 0]);
  assert.equal(result[0].json.бюджет_клиента, '3000');
  assert.match(result[0].json.отклик, /для всех/);
  assert.deepEqual(result[1].json.направления, ['Telegram-боты']);
  assert.equal(result[3].json.детали, 'Собрать сайт');
  assert.equal(result[2].json.опубликовано, '2025-01-02T00:00:00.000Z');
});

test('возвращает пояснение при пустой выборке и распознаёт учебную запись', () => {
  const empty = run([{ title: 'Учебная перевозка коробок', link: project(5) }]);
  assert.match(empty[0].json.результат, /совпадений.*нет/);
  const demo = run([{ demo: true, title: 'Учебная иллюстрация' }]);
  assert.equal(demo[0].json.источник, 'Учебный пример');
  assert.equal(demo[0].json.ссылка, null);
});
