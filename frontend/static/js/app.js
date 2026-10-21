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
  const tabBtnHealth = document.getElementById('tabBtnHealth');
  const btnOpenFinanceFromCard = document.getElementById('btnOpenFinanceFromCard');
  const btnOpenHealthFromCard = document.getElementById('btnOpenHealthFromCard');
  const viewAssistant = document.getElementById('viewAssistant');
  const viewFinance = document.getElementById('viewFinance');
  const viewHealth = document.getElementById('viewHealth');

  function switchTab(target) {
    tabBtnAssistant.classList.remove('active');
    tabBtnFinance.classList.remove('active');
    if (tabBtnHealth) tabBtnHealth.classList.remove('active');
    viewAssistant.classList.remove('active');
    viewFinance.classList.remove('active');
    if (viewHealth) viewHealth.classList.remove('active');

    if (target === 'finance') {
      tabBtnFinance.classList.add('active');
      viewFinance.classList.add('active');
      loadFinanceDashboard();
      loadTransactions();
    } else if (target === 'health') {
      if (tabBtnHealth) tabBtnHealth.classList.add('active');
      if (viewHealth) viewHealth.classList.add('active');
      loadHealthProfile();
      loadDailyHealthSummary();
      loadHealthMeals();
    } else {
      tabBtnAssistant.classList.add('active');
      viewAssistant.classList.add('active');
    }
  }

  if (tabBtnAssistant) tabBtnAssistant.addEventListener('click', () => switchTab('assistant'));
  if (tabBtnFinance) tabBtnFinance.addEventListener('click', () => switchTab('finance'));
  if (tabBtnHealth) tabBtnHealth.addEventListener('click', () => switchTab('health'));
  if (btnOpenFinanceFromCard) btnOpenFinanceFromCard.addEventListener('click', () => switchTab('finance'));
  if (btnOpenHealthFromCard) btnOpenHealthFromCard.addEventListener('click', () => switchTab('health'));


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
        let statusMsg = '[Planned] Live processing will be enabled in subsequent phases.';
        if (decision.intent === 'finance') {
          statusMsg = '[ACTIVE] This module is ready in the Finance Tracker tab!';
        } else if (decision.intent === 'health') {
          statusMsg = '[ACTIVE] This module is ready in the Health Tracker tab!';
        }

        routingBody.innerHTML = [
          `Detected Intent: <strong>${decision.intent.toUpperCase()}</strong>`,
          `Target Module:   <code>${decision.target_module}</code>`,
          `Confidence:      ${Math.round(decision.confidence * 100)}%`,
          `Explanation:     ${decision.explanation}`,
          `\nModule Status:   ${statusMsg}`,
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
  // 10. Health Tracker Module: State & Controller
  // ============================================================================
  let currentHealthProfile = null;
  let currentEstimatedMealDraft = null;
  let currentMealsPage = 1;
  const MEALS_PAGE_SIZE = 15;

  function getLocalIsoDate(d = new Date()) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function getLocalTimeStr(d = new Date()) {
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
  }

  // --- Profile Management ---
  const healthProvisionalBanner = document.getElementById('healthProvisionalBanner');
  const healthProvisionalBadge = document.getElementById('healthProvisionalBadge');
  const btnConfigureProvisionalTarget = document.getElementById('btnConfigureProvisionalTarget');
  const btnOpenHealthProfileModal = document.getElementById('btnOpenHealthProfileModal');
  const healthProfileModal = document.getElementById('healthProfileModal');
  const btnCloseHealthProfileModal = document.getElementById('btnCloseHealthProfileModal');
  const btnCancelHealthProfileModal = document.getElementById('btnCancelHealthProfileModal');
  const healthProfileForm = document.getElementById('healthProfileForm');

  const profileCalorieTarget = document.getElementById('profileCalorieTarget');
  const profileTargetProvisional = document.getElementById('profileTargetProvisional');
  const profileWeight = document.getElementById('profileWeight');
  const profileHeight = document.getElementById('profileHeight');
  const profileAge = document.getElementById('profileAge');
  const profileGender = document.getElementById('profileGender');
  const profileActivityLevel = document.getElementById('profileActivityLevel');
  const profileDietaryPreferences = document.getElementById('profileDietaryPreferences');
  const profileNotes = document.getElementById('profileNotes');

  async function loadHealthProfile() {
    try {
      const res = await fetch('/api/health-tracker/profile');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = await res.json();
      currentHealthProfile = body.data;

      const isProvisional = currentHealthProfile.target_is_provisional;
      if (healthProvisionalBanner) {
        healthProvisionalBanner.style.display = isProvisional ? 'flex' : 'none';
      }
      if (healthProvisionalBadge) {
        healthProvisionalBadge.style.display = isProvisional ? 'inline-block' : 'none';
        healthProvisionalBadge.textContent = isProvisional ? 'Provisional Default' : 'Personal Target';
        healthProvisionalBadge.style.borderColor = isProvisional ? 'rgba(245, 158, 11, 0.4)' : 'rgba(16, 185, 129, 0.4)';
        healthProvisionalBadge.style.color = isProvisional ? '#fbbf24' : '#34d399';
      }
      return currentHealthProfile;
    } catch (err) {
      console.warn('Failed to load health profile:', err);
      return null;
    }
  }

  function openHealthProfileModal() {
    if (!currentHealthProfile) return;
    profileCalorieTarget.value = currentHealthProfile.daily_calorie_target || 2000;
    profileTargetProvisional.checked = !!currentHealthProfile.target_is_provisional;
    profileWeight.value = currentHealthProfile.weight_kg || '';
    profileHeight.value = currentHealthProfile.height_cm || '';
    profileAge.value = currentHealthProfile.age || '';
    profileGender.value = currentHealthProfile.gender || '';
    profileActivityLevel.value = currentHealthProfile.activity_level || '';
    profileDietaryPreferences.value = currentHealthProfile.dietary_preferences || '';
    profileNotes.value = currentHealthProfile.notes || '';

    healthProfileModal.classList.add('active');
  }

  function closeHealthProfileModal() {
    healthProfileModal.classList.remove('active');
  }

  if (btnOpenHealthProfileModal) btnOpenHealthProfileModal.addEventListener('click', openHealthProfileModal);
  if (btnConfigureProvisionalTarget) btnConfigureProvisionalTarget.addEventListener('click', openHealthProfileModal);
  if (btnCloseHealthProfileModal) btnCloseHealthProfileModal.addEventListener('click', closeHealthProfileModal);
  if (btnCancelHealthProfileModal) btnCancelHealthProfileModal.addEventListener('click', closeHealthProfileModal);

  if (healthProfileForm) {
    healthProfileForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const payload = {
          daily_calorie_target: parseInt(profileCalorieTarget.value, 10),
          target_is_provisional: profileTargetProvisional.checked,
          weight_kg: profileWeight.value ? parseFloat(profileWeight.value) : null,
          height_cm: profileHeight.value ? parseFloat(profileHeight.value) : null,
          age: profileAge.value ? parseInt(profileAge.value, 10) : null,
          gender: profileGender.value.trim() || null,
          activity_level: profileActivityLevel.value || null,
          dietary_preferences: profileDietaryPreferences.value.trim() || null,
          notes: profileNotes.value.trim() || null,
        };

        const res = await fetch('/api/health-tracker/profile', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody.error || `Failed to update profile: HTTP ${res.status}`);
        }

        const resData = await res.json();
        currentHealthProfile = resData.data;
        closeHealthProfileModal();
        showToast('Health profile and calorie target updated!', 'success');
        loadHealthProfile();
        loadDailyHealthSummary();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // --- Daily Nutrition Summary & Dashboard Metrics ---
  const healthStatConsumed = document.getElementById('healthStatConsumed');
  const healthStatTarget = document.getElementById('healthStatTarget');
  const healthStatRemaining = document.getElementById('healthStatRemaining');
  const healthStatPercent = document.getElementById('healthStatPercent');
  const healthCalorieProgressBar = document.getElementById('healthCalorieProgressBar');
  const healthSummaryDateLabel = document.getElementById('healthSummaryDateLabel');

  const healthStatProtein = document.getElementById('healthStatProtein');
  const healthStatCarbs = document.getElementById('healthStatCarbs');
  const healthStatFat = document.getElementById('healthStatFat');
  const healthProteinBar = document.getElementById('healthProteinBar');
  const healthCarbsBar = document.getElementById('healthCarbsBar');
  const healthFatBar = document.getElementById('healthFatBar');

  const healthBreakfastCal = document.getElementById('healthBreakfastCal');
  const healthLunchCal = document.getElementById('healthLunchCal');
  const healthDinnerCal = document.getElementById('healthDinnerCal');
  const healthSnackCal = document.getElementById('healthSnackCal');

  async function loadDailyHealthSummary() {
    try {
      const clientDate = getLocalIsoDate();
      const res = await fetch(`/api/health-tracker/daily-summary?client_date=${clientDate}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = await res.json();
      const summary = body.data;

      if (healthStatConsumed) healthStatConsumed.textContent = summary.calories_consumed.toLocaleString();
      if (healthStatTarget) healthStatTarget.textContent = summary.calorie_target.toLocaleString();
      if (healthStatRemaining) healthStatRemaining.textContent = summary.calories_remaining.toLocaleString();
      if (healthStatPercent) healthStatPercent.textContent = `${summary.percentage_consumed}%`;

      if (healthCalorieProgressBar) {
        const pct = Math.min(100, summary.percentage_consumed);
        healthCalorieProgressBar.style.width = `${pct}%`;
        if (summary.calories_consumed > summary.calorie_target) {
          healthCalorieProgressBar.style.background = 'linear-gradient(90deg, #f59e0b, #ef4444)';
        } else {
          healthCalorieProgressBar.style.background = 'linear-gradient(90deg, #10b981, #34d399)';
        }
      }

      if (healthSummaryDateLabel) {
        healthSummaryDateLabel.textContent = summary.client_date;
      }

      const p = parseFloat(summary.total_protein_g) || 0;
      const c = parseFloat(summary.total_carbs_g) || 0;
      const f = parseFloat(summary.total_fat_g) || 0;
      if (healthStatProtein) healthStatProtein.textContent = p.toFixed(1);
      if (healthStatCarbs) healthStatCarbs.textContent = c.toFixed(1);
      if (healthStatFat) healthStatFat.textContent = f.toFixed(1);

      const macroTotal = (p * 4) + (c * 4) + (f * 9);
      if (macroTotal > 0) {
        if (healthProteinBar) healthProteinBar.style.width = `${Math.round(((p * 4) / macroTotal) * 100)}%`;
        if (healthCarbsBar) healthCarbsBar.style.width = `${Math.round(((c * 4) / macroTotal) * 100)}%`;
        if (healthFatBar) healthFatBar.style.width = `${Math.round(((f * 9) / macroTotal) * 100)}%`;
      } else {
        if (healthProteinBar) healthProteinBar.style.width = '0%';
        if (healthCarbsBar) healthCarbsBar.style.width = '0%';
        if (healthFatBar) healthFatBar.style.width = '0%';
      }

      const typeMap = {};
      summary.meal_type_breakdown.forEach(item => {
        typeMap[item.meal_type] = item.calories;
      });
      if (healthBreakfastCal) healthBreakfastCal.textContent = `${typeMap['breakfast'] || 0} kcal`;
      if (healthLunchCal) healthLunchCal.textContent = `${typeMap['lunch'] || 0} kcal`;
      if (healthDinnerCal) healthDinnerCal.textContent = `${typeMap['dinner'] || 0} kcal`;
      if (healthSnackCal) healthSnackCal.textContent = `${typeMap['snack'] || 0} kcal`;

    } catch (err) {
      console.warn('Failed to load daily health summary:', err);
    }
  }

  // --- Meal History & List Management ---
  const mealsContainer = document.getElementById('mealsContainer');
  const healthFilterDate = document.getElementById('healthFilterDate');
  const healthFilterType = document.getElementById('healthFilterType');
  const btnResetHealthFilters = document.getElementById('btnResetHealthFilters');
  const mealsPaginationControls = document.getElementById('mealsPaginationControls');
  const btnPrevMealsPage = document.getElementById('btnPrevMealsPage');
  const btnNextMealsPage = document.getElementById('btnNextMealsPage');
  const mealsPageIndicator = document.getElementById('mealsPageIndicator');

  if (healthFilterDate && !healthFilterDate.value) {
    healthFilterDate.value = getLocalIsoDate();
  }

  async function loadHealthMeals(page = 1) {
    currentMealsPage = page;
    if (!mealsContainer) return;

    mealsContainer.innerHTML = '<div class="state-box"><span class="state-icon">⏳</span><p>Loading meal history...</p></div>';

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: MEALS_PAGE_SIZE.toString(),
      });
      if (healthFilterDate && healthFilterDate.value) {
        params.append('start_date', healthFilterDate.value);
        params.append('end_date', healthFilterDate.value);
      }
      if (healthFilterType && healthFilterType.value) {
        params.append('meal_type', healthFilterType.value);
      }

      const res = await fetch(`/api/health-tracker/meals?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = await res.json();
      const paged = body.data;

      if (!paged.items || paged.items.length === 0) {
        mealsContainer.innerHTML = `
          <div class="state-box">
            <span class="state-icon">🥗</span>
            <strong>No meals found</strong>
            <p>No meals match the selected date or filters. Log a meal above to track your calories.</p>
          </div>
        `;
        if (mealsPaginationControls) mealsPaginationControls.style.display = 'none';
        return;
      }

      mealsContainer.innerHTML = '';
      paged.items.forEach(meal => {
        const itemEl = document.createElement('div');
        itemEl.className = 'tx-item';
        itemEl.id = `meal-item-${meal.id}`;

        const typeClass = `meal-type-${meal.meal_type}`;
        const p = meal.protein_g ? `${parseFloat(meal.protein_g).toFixed(1)}g P` : '';
        const c = meal.carbs_g ? `${parseFloat(meal.carbs_g).toFixed(1)}g C` : '';
        const f = meal.fat_g ? `${parseFloat(meal.fat_g).toFixed(1)}g F` : '';
        const macrosArr = [p, c, f].filter(Boolean);
        const macrosStr = macrosArr.length > 0 ? ` &bull; ${macrosArr.join(', ')}` : '';

        itemEl.innerHTML = `
          <div class="tx-info">
            <div class="tx-top-line">
              <span class="meal-type-badge ${typeClass}">${meal.meal_type}</span>
              <span class="tx-desc" style="font-weight: 600;">${escapeHtml(meal.food_items)}</span>
              ${meal.is_estimated ? '<span class="pill-badge" style="font-size: 0.68rem; background: rgba(56, 189, 248, 0.12); color: #38bdf8;">Estimated</span>' : ''}
            </div>
            <div class="tx-bottom-line">
              <span>📅 ${meal.meal_date} ${meal.meal_time ? `&bull; ⏰ ${meal.meal_time}` : ''}</span>
              ${meal.portion_notes ? `<span>&bull; <em>${escapeHtml(meal.portion_notes)}</em></span>` : ''}
              ${macrosStr ? `<span>${macrosStr}</span>` : ''}
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.85rem;">
            <div style="text-align: right;">
              <span style="font-size: 1.15rem; font-weight: 700; color: #34d399; font-family: var(--font-mono);">
                ${meal.calories} kcal
              </span>
            </div>
            <div style="display: flex; gap: 0.35rem;">
              <button type="button" class="btn-secondary btn-edit-meal" data-id="${meal.id}" title="Edit meal" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">✏️</button>
              <button type="button" class="btn-secondary btn-delete-meal" data-id="${meal.id}" title="Delete meal" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; color: #f87171;">🗑️</button>
            </div>
          </div>
        `;
        mealsContainer.appendChild(itemEl);
      });

      mealsContainer.querySelectorAll('.btn-edit-meal').forEach(btn => {
        btn.addEventListener('click', () => openMealModalForEdit(btn.getAttribute('data-id')));
      });
      mealsContainer.querySelectorAll('.btn-delete-meal').forEach(btn => {
        btn.addEventListener('click', () => deleteMeal(btn.getAttribute('data-id')));
      });

      if (mealsPaginationControls) {
        if (paged.total_pages > 1) {
          mealsPaginationControls.style.display = 'flex';
          mealsPageIndicator.textContent = `Page ${paged.page} of ${paged.total_pages} (${paged.total} meals)`;
          btnPrevMealsPage.disabled = paged.page <= 1;
          btnNextMealsPage.disabled = paged.page >= paged.total_pages;
        } else {
          mealsPaginationControls.style.display = 'none';
        }
      }

    } catch (err) {
      mealsContainer.innerHTML = `<div class="state-box"><span class="state-icon">⚠️</span><p>Error loading meals: ${err.message}</p></div>`;
    }
  }

  if (healthFilterDate) healthFilterDate.addEventListener('change', () => loadHealthMeals(1));
  if (healthFilterType) healthFilterType.addEventListener('change', () => loadHealthMeals(1));
  if (btnResetHealthFilters) {
    btnResetHealthFilters.addEventListener('click', () => {
      if (healthFilterDate) healthFilterDate.value = getLocalIsoDate();
      if (healthFilterType) healthFilterType.value = '';
      loadHealthMeals(1);
    });
  }
  if (btnPrevMealsPage) btnPrevMealsPage.addEventListener('click', () => {
    if (currentMealsPage > 1) loadHealthMeals(currentMealsPage - 1);
  });
  if (btnNextMealsPage) btnNextMealsPage.addEventListener('click', () => {
    loadHealthMeals(currentMealsPage + 1);
  });

  // --- Natural-Language Meal Estimation & Review ---
  const healthNlpForm = document.getElementById('healthNlpForm');
  const healthNlpInput = document.getElementById('healthNlpInput');
  const btnHealthNlpEstimate = document.getElementById('btnHealthNlpEstimate');
  const healthMealReviewCard = document.getElementById('healthMealReviewCard');
  const healthAssumedPortionsList = document.getElementById('healthAssumedPortionsList');
  const healthEstimateAlertBanner = document.getElementById('healthEstimateAlertBanner');
  const healthMealReviewForm = document.getElementById('healthMealReviewForm');
  const btnDiscardHealthReview = document.getElementById('btnDiscardHealthReview');

  const reviewMealType = document.getElementById('reviewMealType');
  const reviewMealCalories = document.getElementById('reviewMealCalories');
  const reviewMealDate = document.getElementById('reviewMealDate');
  const reviewMealTime = document.getElementById('reviewMealTime');
  const reviewMealFoodItems = document.getElementById('reviewMealFoodItems');
  const reviewMealPortionNotes = document.getElementById('reviewMealPortionNotes');
  const reviewMealProtein = document.getElementById('reviewMealProtein');
  const reviewMealCarbs = document.getElementById('reviewMealCarbs');
  const reviewMealFat = document.getElementById('reviewMealFat');

  document.querySelectorAll('#viewHealth .quick-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const phrase = chip.getAttribute('data-phrase');
      if (healthNlpInput && phrase) {
        healthNlpInput.value = phrase;
        healthNlpInput.focus();
      }
    });
  });

  if (healthNlpForm) {
    healthNlpForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = healthNlpInput.value.trim();
      if (!text) return;

      btnHealthNlpEstimate.disabled = true;
      btnHealthNlpEstimate.textContent = 'Estimating...';

      try {
        const clientDate = getLocalIsoDate();
        const res = await fetch('/api/health-tracker/estimate-meal', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text,
            meal_date: clientDate,
          }),
        });

        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody.error || `Estimation failed: HTTP ${res.status}`);
        }

        const resData = await res.json();
        const draft = resData.data;
        currentEstimatedMealDraft = draft;

        healthAssumedPortionsList.innerHTML = '';
        draft.items.forEach(it => {
          const row = document.createElement('div');
          row.className = `portion-item-row ${!it.is_supported ? 'portion-item-warning' : ''}`;
          row.innerHTML = `
            <div>
              <strong>${escapeHtml(it.matched_food_name || it.raw_item_text)}</strong>
              <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">${escapeHtml(it.assumed_portion)}</span>
            </div>
            <div style="text-align: right;">
              <span style="font-weight: 700; color: ${it.is_supported ? '#34d399' : '#f87171'};">
                ${it.calories} kcal
              </span>
              ${it.protein_g ? `<span style="font-size: 0.72rem; color: var(--text-muted); display: block;">${it.protein_g}g P &bull; ${it.carbs_g}g C &bull; ${it.fat_g}g F</span>` : ''}
            </div>
          `;
          healthAssumedPortionsList.appendChild(row);
        });

        if (draft.has_unsupported_items) {
          healthEstimateAlertBanner.style.display = 'block';
          healthEstimateAlertBanner.style.background = 'rgba(239, 68, 68, 0.1)';
          healthEstimateAlertBanner.style.border = '1px solid rgba(239, 68, 68, 0.3)';
          healthEstimateAlertBanner.style.color = '#fca5a5';
          healthEstimateAlertBanner.innerHTML = `
            ⚠️ <strong>Unsupported Foods Flagged:</strong> Could not find verified reference nutritional data for: <em>${escapeHtml(draft.unsupported_items.join(', '))}</em>.<br>
            Please enter your estimated calories manually in the form below before confirming.
          `;
        } else {
          healthEstimateAlertBanner.style.display = 'block';
          healthEstimateAlertBanner.style.background = 'rgba(16, 185, 129, 0.08)';
          healthEstimateAlertBanner.style.border = '1px solid rgba(16, 185, 129, 0.25)';
          healthEstimateAlertBanner.style.color = '#6ee7b7';
          healthEstimateAlertBanner.innerHTML = `
            ✓ Standard reference portions applied. Total estimated: <strong>${draft.total_calories} kcal</strong>. Please review and confirm to save.
          `;
        }

        reviewMealType.value = draft.interpreted.meal_type;
        reviewMealCalories.value = draft.interpreted.calories;
        reviewMealDate.value = draft.interpreted.meal_date || clientDate;
        reviewMealTime.value = draft.interpreted.meal_time || getLocalTimeStr();
        reviewMealFoodItems.value = draft.interpreted.food_items;
        reviewMealPortionNotes.value = draft.interpreted.portion_notes || '';
        reviewMealProtein.value = draft.interpreted.protein_g ? parseFloat(draft.interpreted.protein_g) : '';
        reviewMealCarbs.value = draft.interpreted.carbs_g ? parseFloat(draft.interpreted.carbs_g) : '';
        reviewMealFat.value = draft.interpreted.fat_g ? parseFloat(draft.interpreted.fat_g) : '';

        healthMealReviewCard.classList.add('active');
        healthMealReviewCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btnHealthNlpEstimate.disabled = false;
        btnHealthNlpEstimate.textContent = 'Estimate & Review';
      }
    });
  }

  if (btnDiscardHealthReview) {
    btnDiscardHealthReview.addEventListener('click', () => {
      healthMealReviewCard.classList.remove('active');
      currentEstimatedMealDraft = null;
      if (healthNlpInput) healthNlpInput.value = '';
    });
  }

  if (healthMealReviewForm) {
    healthMealReviewForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const payload = {
          meal_type: reviewMealType.value,
          calories: parseInt(reviewMealCalories.value, 10),
          meal_date: reviewMealDate.value,
          meal_time: reviewMealTime.value.trim() || null,
          food_items: reviewMealFoodItems.value.trim(),
          portion_notes: reviewMealPortionNotes.value.trim() || null,
          protein_g: reviewMealProtein.value ? parseFloat(reviewMealProtein.value) : null,
          carbs_g: reviewMealCarbs.value ? parseFloat(reviewMealCarbs.value) : null,
          fat_g: reviewMealFat.value ? parseFloat(reviewMealFat.value) : null,
          is_estimated: true,
          estimation_notes: currentEstimatedMealDraft ? currentEstimatedMealDraft.message : 'Confirmed from estimation draft',
        };

        const res = await fetch('/api/health-tracker/meals', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody.error || `Failed to save meal: HTTP ${res.status}`);
        }

        healthMealReviewCard.classList.remove('active');
        currentEstimatedMealDraft = null;
        if (healthNlpInput) healthNlpInput.value = '';

        showToast('Meal confirmed and saved to your health ledger!', 'success');
        loadDailyHealthSummary();
        loadHealthMeals(1);

      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // --- Manual Meal Entry / Edit Modal ---
  const mealModal = document.getElementById('mealModal');
  const mealModalTitle = document.getElementById('mealModalTitle');
  const btnCloseMealModal = document.getElementById('btnCloseMealModal');
  const btnCancelMealModal = document.getElementById('btnCancelMealModal');
  const btnOpenNewMealModal = document.getElementById('btnOpenNewMealModal');
  const modalMealForm = document.getElementById('modalMealForm');
  const modalMealId = document.getElementById('modalMealId');

  const modalMealType = document.getElementById('modalMealType');
  const modalMealFoodItems = document.getElementById('modalMealFoodItems');
  const modalMealCalories = document.getElementById('modalMealCalories');
  const modalMealPortionNotes = document.getElementById('modalMealPortionNotes');
  const modalMealProtein = document.getElementById('modalMealProtein');
  const modalMealCarbs = document.getElementById('modalMealCarbs');
  const modalMealFat = document.getElementById('modalMealFat');
  const modalMealDate = document.getElementById('modalMealDate');
  const modalMealTime = document.getElementById('modalMealTime');
  const modalMealNotes = document.getElementById('modalMealNotes');

  function openNewMealModal() {
    modalMealId.value = '';
    mealModalTitle.textContent = 'Log New Meal';
    modalMealForm.reset();
    modalMealDate.value = getLocalIsoDate();
    modalMealTime.value = getLocalTimeStr();
    mealModal.classList.add('active');
  }

  async function openMealModalForEdit(mealId) {
    try {
      const res = await fetch(`/api/health-tracker/meals/${mealId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = await res.json();
      const meal = body.data;

      modalMealId.value = meal.id;
      mealModalTitle.textContent = 'Edit Meal Log';
      modalMealType.value = meal.meal_type;
      modalMealFoodItems.value = meal.food_items;
      modalMealCalories.value = meal.calories;
      modalMealPortionNotes.value = meal.portion_notes || '';
      modalMealProtein.value = meal.protein_g ? parseFloat(meal.protein_g) : '';
      modalMealCarbs.value = meal.carbs_g ? parseFloat(meal.carbs_g) : '';
      modalMealFat.value = meal.fat_g ? parseFloat(meal.fat_g) : '';
      modalMealDate.value = meal.meal_date;
      modalMealTime.value = meal.meal_time || '';
      modalMealNotes.value = meal.notes || '';

      mealModal.classList.add('active');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function closeMealModal() {
    mealModal.classList.remove('active');
  }

  if (btnOpenNewMealModal) btnOpenNewMealModal.addEventListener('click', openNewMealModal);
  if (btnCloseMealModal) btnCloseMealModal.addEventListener('click', closeMealModal);
  if (btnCancelMealModal) btnCancelMealModal.addEventListener('click', closeMealModal);

  if (modalMealForm) {
    modalMealForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const isEdit = !!modalMealId.value;
        const payload = {
          meal_type: modalMealType.value,
          food_items: modalMealFoodItems.value.trim(),
          calories: parseInt(modalMealCalories.value, 10),
          portion_notes: modalMealPortionNotes.value.trim() || null,
          protein_g: modalMealProtein.value ? parseFloat(modalMealProtein.value) : null,
          carbs_g: modalMealCarbs.value ? parseFloat(modalMealCarbs.value) : null,
          fat_g: modalMealFat.value ? parseFloat(modalMealFat.value) : null,
          meal_date: modalMealDate.value,
          meal_time: modalMealTime.value.trim() || null,
          notes: modalMealNotes.value.trim() || null,
        };

        const url = isEdit ? `/api/health-tracker/meals/${modalMealId.value}` : '/api/health-tracker/meals';
        const method = isEdit ? 'PUT' : 'POST';

        const res = await fetch(url, {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody.error || `Failed to save meal: HTTP ${res.status}`);
        }

        closeMealModal();
        showToast(isEdit ? 'Meal updated successfully!' : 'Meal logged successfully!', 'success');
        loadDailyHealthSummary();
        loadHealthMeals(currentMealsPage);

      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  async function deleteMeal(mealId) {
    if (!confirm('Are you sure you want to delete this meal log?')) return;
    try {
      const res = await fetch(`/api/health-tracker/meals/${mealId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showToast('Meal log deleted.', 'success');
      loadDailyHealthSummary();
      loadHealthMeals(currentMealsPage);
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // ============================================================================
  // 11. PWA Service Worker & Install Prompt
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
