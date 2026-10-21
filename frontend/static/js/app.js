/**
 * Aanya Assistant & Finance Tracker - Frontend Controller
 * Manages health check verification, coordinator previews, PWA registration,
 * and the complete Finance Tracker module (CRUD, SQL metrics, NLP draft confirmation).
 */

document.addEventListener('DOMContentLoaded', () => {
  // ============================================================================
  // 1. Navigation Tabs Management
  // ============================================================================
  const tabBtnAssistant = document.getElementById('tabBtnAssistant');
  const tabBtnFinance = document.getElementById('tabBtnFinance');
  const btnOpenFinanceFromCard = document.getElementById('btnOpenFinanceFromCard');
  const viewAssistant = document.getElementById('viewAssistant');
  const viewFinance = document.getElementById('viewFinance');

  function switchTab(target) {
    if (target === 'finance') {
      tabBtnAssistant.classList.remove('active');
      tabBtnFinance.classList.add('active');
      viewAssistant.classList.remove('active');
      viewFinance.classList.add('active');
      loadFinanceDashboard();
      loadTransactions();
    } else {
      tabBtnFinance.classList.remove('active');
      tabBtnAssistant.classList.add('active');
      viewFinance.classList.remove('active');
      viewAssistant.classList.add('active');
    }
  }

  if (tabBtnAssistant) tabBtnAssistant.addEventListener('click', () => switchTab('assistant'));
  if (tabBtnFinance) tabBtnFinance.addEventListener('click', () => switchTab('finance'));
  if (btnOpenFinanceFromCard) btnOpenFinanceFromCard.addEventListener('click', () => switchTab('finance'));

  // ============================================================================
  // 2. Core Health & System Verification
  // ============================================================================
  const statusBadge = document.getElementById('statusBadge');
  const statusText = document.getElementById('statusText');
  const refreshBtn = document.getElementById('refreshHealthBtn');
  const diagDb = document.getElementById('diagDb');
  const diagEnv = document.getElementById('diagEnv');
  const diagVersion = document.getElementById('diagVersion');
  const diagScheduler = document.getElementById('diagScheduler');

  async function checkHealth() {
    statusBadge.className = 'status-badge checking';
    statusText.textContent = 'Checking...';

    try {
      const response = await fetch('/api/health', {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        cache: 'no-store',
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const json = await response.json();
      const data = json.data || {};

      if (data.status === 'ok') {
        statusBadge.className = 'status-badge online';
        statusText.textContent = 'Online';
      } else {
        statusBadge.className = 'status-badge degraded';
        statusText.textContent = 'Degraded';
      }

      diagDb.textContent = data.database || 'unknown';
      diagEnv.textContent = data.environment || 'development';
      diagVersion.textContent = data.version || '0.1.0';
      diagScheduler.textContent = data.scheduler?.running ? 'Running (in-memory)' : 'Stopped';

    } catch (err) {
      statusBadge.className = 'status-badge offline';
      statusText.textContent = 'Backend Offline';
      diagDb.textContent = 'Unreachable';
      diagEnv.textContent = '-';
      diagVersion.textContent = '-';
      diagScheduler.textContent = '-';
      console.warn('Backend health check error:', err);
    }
  }

  checkHealth();
  if (refreshBtn) refreshBtn.addEventListener('click', (e) => { e.preventDefault(); checkHealth(); });

  // ============================================================================
  // 3. Coordinator Routing Preview
  // ============================================================================
  const queryForm = document.getElementById('queryForm');
  const queryInput = document.getElementById('queryInput');
  const routeBtn = document.getElementById('routeBtn');
  const routingOutput = document.getElementById('routingOutput');
  const routingBody = document.getElementById('routingBody');

  if (queryForm) {
    queryForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = queryInput.value.trim();
      if (!text) return;

      routeBtn.disabled = true;
      routeBtn.textContent = 'Routing...';

      try {
        const response = await fetch('/api/coordinator/route', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify({ text: text, context: { client: 'web' } }),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}: Failed to reach coordinator.`);

        const res = await response.json();
        const decision = res.data;

        routingOutput.classList.add('active');
        const isModuleActive = decision.intent === 'finance';
        routingBody.innerHTML = [
          `Detected Intent: <strong>${decision.intent.toUpperCase()}</strong>`,
          `Target Module:   <code>${decision.target_module}</code>`,
          `Confidence:      ${Math.round(decision.confidence * 100)}%`,
          `Explanation:     ${decision.explanation}`,
          `\nModule Status:   ${isModuleActive ? '[ACTIVE] This module is ready in the Finance Tracker tab!' : '[Planned] Live processing will be enabled in subsequent phases.'}`,
        ].join('\n');

      } catch (err) {
        routingOutput.classList.add('active');
        routingBody.innerHTML = `Error checking coordinator: ${err.message}\nMake sure the FastAPI backend is running and reachable at /api.`;
      } finally {
        routeBtn.disabled = false;
        routeBtn.textContent = 'Test Routing';
      }
    });
  }

  // ============================================================================
  // 4. Utility: Toast & Currency Formatter
  // ============================================================================
  const toastContainer = document.getElementById('toastContainer');

  function showToast(message, type = 'success') {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✓' : '⚠️';
    toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  function formatINR(amount) {
    const num = Number(amount);
    if (isNaN(num)) return '₹0.00';
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, (m) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
  }

  // ============================================================================
  // 5. Finance Module: Categories & Setup
  // ============================================================================
  let categoriesCache = [];

  async function loadCategories() {
    try {
      const res = await fetch('/api/finance/categories');
      if (res.ok) {
        const json = await res.json();
        categoriesCache = json.data || [];
        populateCategoryDropdowns();
      }
    } catch (e) {
      console.warn('Failed to load categories:', e);
    }
  }

  function populateCategoryDropdowns() {
    const selects = [
      document.getElementById('reviewCategory'),
      document.getElementById('modalCategory'),
      document.getElementById('filterCategory')
    ];

    selects.forEach(sel => {
      if (!sel) return;
      const isFilter = sel.id === 'filterCategory';
      const existingVal = sel.value;
      sel.innerHTML = isFilter ? '<option value="">All Categories</option>' : '';
      categoriesCache.forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat;
        opt.textContent = cat;
        sel.appendChild(opt);
      });
      if (existingVal) sel.value = existingVal;
    });
  }

  loadCategories();

  // ============================================================================
  // 6. Finance Module: Dashboard Metrics
  // ============================================================================
  const finStatIncome = document.getElementById('finStatIncome');
  const finStatExpense = document.getElementById('finStatExpense');
  const finStatBalance = document.getElementById('finStatBalance');
  const categoryBreakdownList = document.getElementById('categoryBreakdownList');

  async function loadFinanceDashboard() {
    try {
      const res = await fetch('/api/finance/dashboard');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const data = json.data;

      // Update stat cards
      if (finStatIncome) finStatIncome.textContent = formatINR(data.total_income_this_month);
      if (finStatExpense) finStatExpense.textContent = formatINR(data.total_expenses_this_month);
      
      if (finStatBalance) {
        finStatBalance.textContent = formatINR(data.net_balance_this_month);
        const netNum = Number(data.net_balance_this_month);
        finStatBalance.className = `stat-value ${netNum >= 0 ? 'balance-pos' : 'balance-neg'}`;
      }

      // Update category breakdown
      renderCategoryBreakdown(data.category_breakdown, data.period_total_expenses);

    } catch (err) {
      console.warn('Failed to load finance dashboard metrics:', err);
    }
  }

  function renderCategoryBreakdown(breakdown, totalExpenses) {
    if (!categoryBreakdownList) return;
    if (!breakdown || breakdown.length === 0) {
      categoryBreakdownList.innerHTML = `
        <div style="font-size: 0.85rem; color: var(--text-muted); text-align: center; padding: 1rem 0;">
          No expense transactions recorded for this period yet.
        </div>`;
      return;
    }

    categoryBreakdownList.innerHTML = breakdown.map(cat => `
      <div class="category-row">
        <div class="category-row-meta">
          <span style="font-weight: 600;">${escapeHtml(cat.category)}</span>
          <span style="font-family: var(--font-mono); font-weight: 600;">
            ${formatINR(cat.total_amount)}
            <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 0.3rem;">(${cat.percentage_of_total}%)</span>
          </span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" style="width: ${Math.min(100, Math.max(2, cat.percentage_of_total))}%;"></div>
        </div>
      </div>
    `).join('');
  }

  // ============================================================================
  // 7. Finance Module: Transactions List & Pagination
  // ============================================================================
  const transactionsContainer = document.getElementById('transactionsContainer');
  const txCountBadge = document.getElementById('txCountBadge');
  const paginationControls = document.getElementById('paginationControls');
  const pageIndicator = document.getElementById('pageIndicator');
  const btnPrevPage = document.getElementById('btnPrevPage');
  const btnNextPage = document.getElementById('btnNextPage');

  const filterStartDate = document.getElementById('filterStartDate');
  const filterEndDate = document.getElementById('filterEndDate');
  const filterType = document.getElementById('filterType');
  const filterCategory = document.getElementById('filterCategory');
  const btnApplyFilters = document.getElementById('btnApplyFilters');
  const btnResetFilters = document.getElementById('btnResetFilters');

  let currentPage = 1;
  const pageSize = 15;
  let totalPages = 1;

  async function loadTransactions() {
    if (!transactionsContainer) return;
    transactionsContainer.innerHTML = `
      <div class="state-box">
        <span class="status-dot" style="width: 12px; height: 12px; background: var(--accent-cyan); animation: pulse 1.5s infinite ease-in-out;"></span>
        <span>Loading transactions from PostgreSQL...</span>
      </div>`;

    const params = new URLSearchParams({
      page: currentPage,
      page_size: pageSize,
    });

    if (filterStartDate?.value) params.append('start_date', filterStartDate.value);
    if (filterEndDate?.value) params.append('end_date', filterEndDate.value);
    if (filterType?.value) params.append('type', filterType.value);
    if (filterCategory?.value) params.append('category', filterCategory.value);

    try {
      const res = await fetch(`/api/finance/transactions?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const paged = json.data;

      totalPages = paged.total_pages || 1;
      if (txCountBadge) txCountBadge.textContent = `${paged.total} transaction${paged.total === 1 ? '' : 's'}`;

      if (paged.items.length === 0) {
        transactionsContainer.innerHTML = `
          <div class="state-box">
            <span class="state-icon" aria-hidden="true">💳</span>
            <strong>No transactions found</strong>
            <p style="font-size: 0.8rem;">Add your first transaction above or use natural-language quick entry.</p>
          </div>`;
        if (paginationControls) paginationControls.style.display = 'none';
        return;
      }

      transactionsContainer.innerHTML = paged.items.map(tx => {
        const isIncome = tx.type === 'income';
        const sign = isIncome ? '+' : '-';
        const amountClass = isIncome ? 'income' : 'expense';

        return `
          <div class="tx-item" data-id="${tx.id}">
            <div class="tx-info">
              <span class="tx-desc">${escapeHtml(tx.description)}</span>
              <div class="tx-meta">
                <span class="tx-category-badge">${escapeHtml(tx.category)}</span>
                <span>${tx.transaction_date}</span>
                <span>&bull;</span>
                <span>${escapeHtml(tx.payment_method)}</span>
                ${tx.notes ? `<span>&bull;</span> <span style="font-style: italic;">${escapeHtml(tx.notes)}</span>` : ''}
              </div>
            </div>
            <div class="tx-amount-col">
              <span class="tx-amount ${amountClass}">${sign}${formatINR(tx.amount)}</span>
              <div class="tx-item-actions">
                <button type="button" class="btn-icon edit-btn" data-id="${tx.id}" title="Edit transaction">✏️ Edit</button>
                <button type="button" class="btn-icon delete delete-btn" data-id="${tx.id}" title="Delete transaction">🗑️</button>
              </div>
            </div>
          </div>
        `;
      }).join('');

      // Wire up edit & delete buttons
      transactionsContainer.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', () => openEditModal(btn.dataset.id));
      });
      transactionsContainer.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteTransaction(btn.dataset.id));
      });

      // Update pagination
      if (paginationControls) {
        if (totalPages > 1) {
          paginationControls.style.display = 'flex';
          if (pageIndicator) pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
          if (btnPrevPage) btnPrevPage.disabled = currentPage <= 1;
          if (btnNextPage) btnNextPage.disabled = currentPage >= totalPages;
        } else {
          paginationControls.style.display = 'none';
        }
      }

    } catch (err) {
      transactionsContainer.innerHTML = `
        <div class="state-box" style="border-color: var(--status-error-border);">
          <span style="color: var(--status-error-text);">Failed to load transactions: ${escapeHtml(err.message)}</span>
          <button type="button" class="btn-secondary" onclick="loadTransactions()">Retry</button>
        </div>`;
    }
  }

  // Pagination button handlers
  if (btnPrevPage) {
    btnPrevPage.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        loadTransactions();
      }
    });
  }
  if (btnNextPage) {
    btnNextPage.addEventListener('click', () => {
      if (currentPage < totalPages) {
        currentPage++;
        loadTransactions();
      }
    });
  }

  // Filter actions
  if (btnApplyFilters) {
    btnApplyFilters.addEventListener('click', () => {
      currentPage = 1;
      loadTransactions();
      loadFinanceDashboard();
    });
  }
  if (btnResetFilters) {
    btnResetFilters.addEventListener('click', () => {
      if (filterStartDate) filterStartDate.value = '';
      if (filterEndDate) filterEndDate.value = '';
      if (filterType) filterType.value = '';
      if (filterCategory) filterCategory.value = '';
      currentPage = 1;
      loadTransactions();
      loadFinanceDashboard();
    });
  }

  // ============================================================================
  // 8. Finance Module: Natural-Language Interpretation & Confirmation
  // ============================================================================
  const nlpForm = document.getElementById('nlpForm');
  const nlpInput = document.getElementById('nlpInput');
  const btnNlpParse = document.getElementById('btnNlpParse');
  const reviewCard = document.getElementById('reviewCard');
  const reviewForm = document.getElementById('reviewForm');
  const reviewConfidence = document.getElementById('reviewConfidence');
  const btnDiscardReview = document.getElementById('btnDiscardReview');

  const reviewType = document.getElementById('reviewType');
  const reviewAmount = document.getElementById('reviewAmount');
  const reviewCategory = document.getElementById('reviewCategory');
  const reviewDescription = document.getElementById('reviewDescription');
  const reviewDate = document.getElementById('reviewDate');
  const reviewPaymentMethod = document.getElementById('reviewPaymentMethod');
  const reviewNotes = document.getElementById('reviewNotes');

  // Quick chips
  document.querySelectorAll('.quick-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      if (nlpInput) {
        nlpInput.value = chip.dataset.phrase;
        if (nlpForm) nlpForm.dispatchEvent(new Event('submit'));
      }
    });
  });

  if (nlpForm) {
    nlpForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = nlpInput.value.trim();
      if (!text) return;

      btnNlpParse.disabled = true;
      btnNlpParse.textContent = 'Interpreting...';

      try {
        const res = await fetch('/api/finance/parse-natural-language', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}: Interpretation failed`);
        const json = await res.json();
        const data = json.data;
        const tx = data.interpreted;

        // Populate Review Card
        reviewType.value = tx.type;
        reviewAmount.value = tx.amount;
        reviewCategory.value = tx.category;
        reviewDescription.value = tx.description;
        reviewDate.value = tx.transaction_date;
        reviewPaymentMethod.value = tx.payment_method;
        reviewNotes.value = tx.notes || '';
        reviewConfidence.textContent = `Confidence: ${Math.round(data.confidence * 100)}%`;

        reviewCard.classList.add('active');
        reviewCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btnNlpParse.disabled = false;
        btnNlpParse.textContent = 'Parse & Review';
      }
    });
  }

  if (btnDiscardReview) {
    btnDiscardReview.addEventListener('click', () => {
      reviewCard.classList.remove('active');
    });
  }

  if (reviewForm) {
    reviewForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        type: reviewType.value,
        amount: parseFloat(reviewAmount.value),
        category: reviewCategory.value,
        description: reviewDescription.value.trim(),
        transaction_date: reviewDate.value,
        payment_method: reviewPaymentMethod.value,
        notes: reviewNotes.value.trim() || null,
      };

      try {
        const res = await fetch('/api/finance/transactions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || 'Failed to save transaction');
        }

        showToast('Transaction confirmed and saved to PostgreSQL!', 'success');
        reviewCard.classList.remove('active');
        if (nlpInput) nlpInput.value = '';

        loadFinanceDashboard();
        loadTransactions();

      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // ============================================================================
  // 9. Finance Module: Manual Entry & Edit Modal
  // ============================================================================
  const txModal = document.getElementById('txModal');
  const btnOpenNewTxModal = document.getElementById('btnOpenNewTxModal');
  const btnCloseTxModal = document.getElementById('btnCloseTxModal');
  const btnCancelModal = document.getElementById('btnCancelModal');
  const modalTxForm = document.getElementById('modalTxForm');
  const modalTitle = document.getElementById('modalTitle');

  const modalTxId = document.getElementById('modalTxId');
  const radioExpense = document.getElementById('radioExpense');
  const radioIncome = document.getElementById('radioIncome');
  const modalAmount = document.getElementById('modalAmount');
  const modalCategory = document.getElementById('modalCategory');
  const modalDescription = document.getElementById('modalDescription');
  const modalDate = document.getElementById('modalDate');
  const modalPaymentMethod = document.getElementById('modalPaymentMethod');
  const modalNotes = document.getElementById('modalNotes');

  function openNewModal() {
    modalTxId.value = '';
    modalTitle.textContent = 'Add New Transaction';
    radioExpense.checked = true;
    modalAmount.value = '';
    modalDescription.value = '';
    modalDate.value = new Date().toISOString().split('T')[0];
    modalPaymentMethod.value = 'UPI';
    modalNotes.value = '';
    if (modalCategory && modalCategory.options.length > 0) {
      modalCategory.selectedIndex = 0;
    }
    txModal.classList.add('active');
  }

  async function openEditModal(txId) {
    try {
      const res = await fetch(`/api/finance/transactions/${txId}`);
      if (!res.ok) throw new Error('Transaction not found');
      const json = await res.json();
      const tx = json.data;

      modalTxId.value = tx.id;
      modalTitle.textContent = 'Edit Transaction';
      if (tx.type === 'income') radioIncome.checked = true;
      else radioExpense.checked = true;

      modalAmount.value = tx.amount;
      modalCategory.value = tx.category;
      modalDescription.value = tx.description;
      modalDate.value = tx.transaction_date;
      modalPaymentMethod.value = tx.payment_method;
      modalNotes.value = tx.notes || '';

      txModal.classList.add('active');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function closeModal() {
    txModal.classList.remove('active');
  }

  if (btnOpenNewTxModal) btnOpenNewTxModal.addEventListener('click', openNewModal);
  if (btnCloseTxModal) btnCloseTxModal.addEventListener('click', closeModal);
  if (btnCancelModal) btnCancelModal.addEventListener('click', closeModal);

  if (modalTxForm) {
    modalTxForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const isEdit = !!modalTxId.value;
      const payload = {
        type: radioIncome.checked ? 'income' : 'expense',
        amount: parseFloat(modalAmount.value),
        category: modalCategory.value,
        description: modalDescription.value.trim(),
        transaction_date: modalDate.value,
        payment_method: modalPaymentMethod.value,
        notes: modalNotes.value.trim() || null,
      };

      try {
        const url = isEdit ? `/api/finance/transactions/${modalTxId.value}` : '/api/finance/transactions';
        const method = isEdit ? 'PUT' : 'POST';

        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.error || 'Failed to save transaction');
        }

        closeModal();
        showToast(isEdit ? 'Transaction updated successfully!' : 'Transaction created successfully!', 'success');
        loadFinanceDashboard();
        loadTransactions();

      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // Delete transaction handler
  async function deleteTransaction(txId) {
    if (!confirm('Are you sure you want to delete this transaction?')) return;
    try {
      const res = await fetch(`/api/finance/transactions/${txId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete transaction');
      showToast('Transaction deleted successfully.', 'success');
      loadFinanceDashboard();
      loadTransactions();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // ============================================================================
  // 10. PWA Service Worker & Install Prompt
  // ============================================================================
  let deferredInstallPrompt = null;
  const installBanner = document.getElementById('installBanner');
  const installBtn = document.getElementById('installBtn');

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js')
        .then((reg) => console.log('[Aanya PWA] Service worker active. Scope:', reg.scope))
        .catch((err) => console.warn('[Aanya PWA] SW registration failed:', err));
    });
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;
    if (installBanner) installBanner.classList.add('visible');
  });

  if (installBtn) {
    installBtn.addEventListener('click', async () => {
      if (!deferredInstallPrompt) return;
      deferredInstallPrompt.prompt();
      await deferredInstallPrompt.userChoice;
      deferredInstallPrompt = null;
      installBanner.classList.remove('visible');
    });
  }

  window.addEventListener('appinstalled', () => {
    if (installBanner) installBanner.classList.remove('visible');
  });
});
