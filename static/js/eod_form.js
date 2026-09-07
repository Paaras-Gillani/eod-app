const params = new URLSearchParams(window.location.search);
const pageId = params.get('page_id');
const pageName = params.get('page_name') || '';

document.getElementById('page_id').value = pageId || '';
document.getElementById('page_name_display').value = pageName;
document.getElementById('page-title').textContent = pageName ? `New EOD - ${pageName}` : 'New EOD';
document.getElementById('report_date').valueAsDate = new Date();

if (!pageId) {
  document.getElementById('extract-status').innerHTML =
    '<div class="status-msg error">No page selected. Go back and pick a page first.</div>';
}

let selectedFile = null;
let lastScreenshotPath = null;

// ---- File picker ----
const dropEl = document.getElementById('upload-drop');
const fileInput = document.getElementById('screenshot_input');
dropEl.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  selectedFile = fileInput.files[0] || null;
  document.getElementById('extract-btn').disabled = !selectedFile;
  document.getElementById('upload-label').textContent = selectedFile
    ? selectedFile.name
    : 'Click to choose today\'s dashboard screenshot';
  dropEl.classList.toggle('has-file', !!selectedFile);
});

// ---- Breakdown table helpers ----
function addRow(tableId, method = '', amount = '') {
  const tbody = document.querySelector(`#${tableId} tbody`);
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input type="text" class="method-input" value="${escapeAttr(method)}" placeholder="e.g. Cash App" /></td>
    <td class="amount-col"><input type="number" step="0.01" class="amount-input" value="${amount}" /></td>
    <td class="remove-col"><button type="button" class="icon-btn" title="Remove">✕</button></td>
  `;
  tr.querySelector('.icon-btn').addEventListener('click', () => {
    tr.remove();
    recalcTotals();
  });
  tr.querySelectorAll('input').forEach(inp => inp.addEventListener('input', recalcTotals));
  tbody.appendChild(tr);
}

function escapeAttr(s) {
  return String(s).replace(/"/g, '&quot;');
}

function readBreakdown(tableId) {
  return Array.from(document.querySelectorAll(`#${tableId} tbody tr`)).map(tr => ({
    method: tr.querySelector('.method-input').value.trim(),
    amount: parseFloat(tr.querySelector('.amount-input').value) || 0,
  })).filter(r => r.method);
}

function sum(items) {
  return items.reduce((acc, i) => acc + i.amount, 0);
}

function recalcTotals() {
  document.getElementById('grand_total_deposit').value =
    sum(readBreakdown('deposit-table')).toFixed(2);
  document.getElementById('redeem_paid_amount').value =
    sum(readBreakdown('redeem-table')).toFixed(2);
}

document.getElementById('add-deposit-row').addEventListener('click', () => addRow('deposit-table'));
document.getElementById('add-redeem-row').addEventListener('click', () => addRow('redeem-table'));

// ---- Extraction ----
document.getElementById('extract-btn').addEventListener('click', async () => {
  if (!selectedFile || !pageName) return;
  const btn = document.getElementById('extract-btn');
  const statusEl = document.getElementById('extract-status');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Reading screenshot...';
  statusEl.innerHTML = '';

  const form = new FormData();
  form.append('page_name', pageName);
  form.append('screenshot', selectedFile);

  try {
    const res = await fetch('/api/vision/extract', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Extraction failed.');
    }

    document.querySelector('#deposit-table tbody').innerHTML = '';
    document.querySelector('#redeem-table tbody').innerHTML = '';
    (data.deposit_breakdown || []).forEach(i => addRow('deposit-table', i.method, i.amount));
    (data.redeem_breakdown || []).forEach(i => addRow('redeem-table', i.method, i.amount));

    document.getElementById('grand_total_deposit').value = (data.grand_total_deposit ?? 0).toFixed(2);
    document.getElementById('redeem_paid_amount').value = (data.redeem_paid_amount ?? sum(data.redeem_breakdown || [])).toFixed(2);
    document.getElementById('redeem_pending_amount').value = (data.redeem_pending_amount ?? 0).toFixed(2);
    lastScreenshotPath = data.screenshot_path || null;

    statusEl.innerHTML = '<div class="status-msg success">Extracted — double check the numbers below before saving.</div>';
  } catch (err) {
    statusEl.innerHTML = `<div class="status-msg error">${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Extract amounts from screenshot';
  }
});

// ---- Submit ----
document.getElementById('eod-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const statusEl = document.getElementById('submit-status');
  const submitBtn = document.getElementById('submit-btn');

  if (!pageId) {
    statusEl.innerHTML = '<div class="status-msg error">No page selected.</div>';
    return;
  }

  const payload = {
    page_id: parseInt(pageId, 10),
    report_date: document.getElementById('report_date').value,
    redeem_processed_count: parseInt(document.getElementById('redeem_processed_count').value || '0', 10),
    redeem_paid_count: parseInt(document.getElementById('redeem_paid_count').value || '0', 10),
    redeem_pending_count: parseInt(document.getElementById('redeem_pending_count').value || '0', 10),
    redeem_paid_amount: parseFloat(document.getElementById('redeem_paid_amount').value || '0'),
    redeem_pending_amount: parseFloat(document.getElementById('redeem_pending_amount').value || '0'),
    grand_total_deposit: parseFloat(document.getElementById('grand_total_deposit').value || '0'),
    deposit_breakdown: readBreakdown('deposit-table'),
    redeem_breakdown: readBreakdown('redeem-table'),
    screenshot_path: lastScreenshotPath,
  };

  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner"></span> Saving...';

  try {
    const res = await fetch('/api/eod', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to save.');
    window.location = `/eod/${data.id}`;
  } catch (err) {
    statusEl.innerHTML = `<div class="status-msg error">${err.message}</div>`;
    submitBtn.disabled = false;
    submitBtn.textContent = 'Save EOD';
  }
});

// Start with one blank row in each table so staff can enter fully manually too.
addRow('deposit-table');
addRow('redeem-table');
