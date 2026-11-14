/**
 * 보험사 공시실 Ulixee Hero passive probe (보험사 비종속 일반 스크립트).
 *
 * 목적
 *   - 보험사 이름을 소스에 넣지 않고, 전달받은 공시실 URL만 열어 구조를 판별한다.
 *   - 판별 결과(최종 URL, 제목, 표/목록 수, 다운로드 후보 링크, onclick 함수명, 스크린샷)를
 *     JSON 한 줄로 stdout에 출력한다. 이 결과로 public_document_catalog_collector 프로파일을 만든다.
 *
 * 안전 경계 (use-ulixee-hero-crawler 스킬)
 *   - 읽기 전용: goto, 렌더 대기, HTML 읽기, 스크린샷만 한다. 클릭·폼 제출·로그인은 하지 않는다.
 *   - CAPTCHA·WAF·접근제어 우회, 프록시/지문 변경은 하지 않는다. 401/403/429 징후는 기록만 하고 멈춘다.
 *
 * 실행
 *   node insurer_disclosure_hero_probe.js --hero-dir <node_modules 상위 폴더> --out-dir <증빙 폴더>
 *        --url <URL1> [--url <URL2> ...] [--timeout-ms 45000]
 *   (보통은 같은 폴더의 insurer_disclosure_hero_probe.py가 config.py 값을 읽어 이 스크립트를 부른다.)
 */
'use strict';

const path = require('path');
const fs = require('fs');
const { createRequire } = require('module');

// ---- 1. 인자 해석: 잘못된 입력이면 즉시 종료코드 2로 끝낸다(테스트 대상) ----
function parseArgs(argv) {
  const args = { urls: [], timeoutMs: 45000, heroDir: '', outDir: '' };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (key === '--url') { args.urls.push(value); i += 1; }
    else if (key === '--timeout-ms') { args.timeoutMs = Number(value); i += 1; }
    else if (key === '--hero-dir') { args.heroDir = value; i += 1; }
    else if (key === '--out-dir') { args.outDir = value; i += 1; }
    else throw new Error(`알 수 없는 인자: ${key}`);
  }
  if (!args.urls.length) throw new Error('--url 이 최소 1개 필요합니다');
  for (const u of args.urls) {
    // http/https 공개 URL만 허용한다(file:, javascript: 등 차단).
    const parsed = new URL(u);
    if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error(`허용되지 않는 URL: ${u}`);
  }
  if (!Number.isInteger(args.timeoutMs) || args.timeoutMs < 1000 || args.timeoutMs > 120000) {
    throw new Error('--timeout-ms 는 1000~120000 정수여야 합니다');
  }
  if (!args.heroDir || !args.outDir) throw new Error('--hero-dir, --out-dir 가 필요합니다');
  return args;
}

// ---- 2. HTML에서 다운로드 후보를 뽑는다(사이트별 선택자를 하드코딩하지 않는 일반 규칙) ----
function analyzeHtml(html) {
  const pick = (re) => Array.from(html.matchAll(re), (m) => m[1]);
  const hrefs = pick(/href\s*=\s*["']([^"']+)["']/gi);
  const onclicks = pick(/onclick\s*=\s*["']([^"']+)["']/gi);
  // PDF·다운로드로 보이는 href (확장자 또는 download/file 키워드)
  const downloadHrefs = hrefs.filter((h) => /\.pdf(\?|$)|download|filedown|fileDown|atch|attach/i.test(h));
  // onclick 안의 함수 이름 빈도: 상세 열기/다운로드 함수 판별 근거
  const fnCount = {};
  for (const oc of onclicks) {
    const m = oc.match(/([A-Za-z_$][\w$.]*)\s*\(/);
    if (m) fnCount[m[1]] = (fnCount[m[1]] || 0) + 1;
  }
  const scripts = pick(/<script[^>]+src\s*=\s*["']([^"']+)["']/gi);
  return {
    html_length: html.length,
    table_count: (html.match(/<table\b/gi) || []).length,
    tr_count: (html.match(/<tr\b/gi) || []).length,
    li_count: (html.match(/<li\b/gi) || []).length,
    form_count: (html.match(/<form\b/gi) || []).length,
    iframe_srcs: pick(/<iframe[^>]+src\s*=\s*["']([^"']+)["']/gi),
    download_hrefs_sample: downloadHrefs.slice(0, 30),
    download_href_count: downloadHrefs.length,
    onclick_functions: fnCount,
    onclick_sample: onclicks.slice(0, 20),
    script_srcs: scripts.slice(0, 40),
    // 페이지 상태 판별 키워드(로그인·차단 징후는 기록만 한다)
    signals: {
      login: /로그인|login/i.test(html),
      captcha: /captcha|자동입력방지/i.test(html),
      blocked: /access denied|접근이 제한|차단/i.test(html),
      pagination: /paging|pagination|pageIndex|pageNo|currentPage/i.test(html),
      sale_stopped_tab: /판매중지|판매종료|판매 중지|판매 종료/.test(html),
      terms_word: /약관/.test(html),
    },
  };
}

// ---- 3. Hero 생성: 같은 프로세스에 HeroCore를 붙인다(외부 Cloud 서버 불필요) ----
async function createHero(heroRequire) {
  const Hero = heroRequire('@ulixee/hero').default;
  try {
    // 권장 방식: TransportBridge로 클라이언트와 Core를 직접 연결
    const HeroCore = heroRequire('@ulixee/hero-core').default;
    const { TransportBridge } = heroRequire('@ulixee/net');
    const { ConnectionToHeroCore } = heroRequire('@ulixee/hero');
    const bridge = new TransportBridge();
    const core = new HeroCore();
    core.addConnection(bridge.transportToClient);
    const connectionToCore = new ConnectionToHeroCore(bridge.transportToCore);
    return { hero: new Hero({ showChrome: false, connectionToCore }), core, mode: 'bridge' };
  } catch (error) {
    // 대체 방식: 기존 hero_mcp_server/src/server.js와 같은 기본 생성자
    return { hero: new Hero({ showChrome: false }), core: null, mode: `default (bridge 실패: ${error.message})` };
  }
}

async function probeOne(hero, url, index, args) {
  const item = { input_url: url, started_at: new Date().toISOString() };
  try {
    const resource = await hero.goto(url, { timeoutMs: args.timeoutMs });
    item.http_status = resource?.response?.statusCode ?? null;
    // 렌더 안정 대기(실패해도 진행: SPA는 늦게 그려질 수 있음)
    try { await hero.waitForPaintingStable({ timeoutMs: 15000 }); } catch (e) { item.paint_wait_error = e.message; }
    item.final_url = await hero.url;
    item.title = await hero.document.title;
    const html = String((await hero.document.documentElement.outerHTML) ?? '');
    item.analysis = analyzeHtml(html);
    // 원본 HTML은 증빙 파일로 저장(대화창에 뿌리지 않음)
    const htmlPath = path.join(args.outDir, `page_${index}.html`);
    fs.writeFileSync(htmlPath, html, 'utf8');
    item.html_path = htmlPath;
    const png = await hero.takeScreenshot({});
    const pngPath = path.join(args.outDir, `page_${index}.png`);
    fs.writeFileSync(pngPath, png);
    item.screenshot_path = pngPath;
    // 401/403/429 등은 접근 통제 신호 → 기록만 하고 추가 시도하지 않는다.
    item.access_state = [401, 403, 407, 429].includes(item.http_status) ? 'blocked_or_limited' : 'public';
  } catch (error) {
    item.error = error.message;
    item.access_state = 'error';
  }
  item.finished_at = new Date().toISOString();
  return item;
}

async function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    process.stdout.write(JSON.stringify({ ok: false, error: error.message }) + '\n');
    process.exit(2);
  }
  fs.mkdirSync(args.outDir, { recursive: true });
  // node_modules가 haness/apps/ulixee_hero_mcp 아래에 있으므로 그 위치 기준으로 require한다.
  const heroRequire = createRequire(path.join(args.heroDir, 'probe_require_anchor.js'));
  const { hero, core, mode } = await createHero(heroRequire);
  const pages = [];
  try {
    // 순차 처리(동시성 1): 서버 부담 최소화
    for (let i = 0; i < args.urls.length; i += 1) pages.push(await probeOne(hero, args.urls[i], i, args));
  } finally {
    try { await hero.close(); } catch (e) { /* 종료 실패는 결과에 영향 없음 */ }
    if (core) { try { await core.close(); } catch (e) { /* 무시 */ } }
  }
  const out = { ok: pages.every((p) => !p.error), hero_mode: mode, pages };
  fs.writeFileSync(path.join(args.outDir, 'probe_result.json'), JSON.stringify(out, null, 2), 'utf8');
  process.stdout.write(JSON.stringify(out) + '\n');
  process.exit(out.ok ? 0 : 1);
}

main().catch((error) => {
  process.stdout.write(JSON.stringify({ ok: false, error: String(error?.stack || error) }) + '\n');
  process.exit(1);
});
