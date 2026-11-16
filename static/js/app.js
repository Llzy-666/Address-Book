/* ==========================================================================
   通讯录 · 前端逻辑（原生 ES6，无框架、无构建工具）
   分层：api 层（统一解包 code/message）→ render 层 → 事件层
   ========================================================================== */

(function () {
  'use strict';

  /* -------------------------------------------------------------- 常量 */

  var API = {
    contacts: '/api/contacts',
    exportUrl: '/api/export',
    templateUrl: '/api/export/template',
    importUrl: '/api/import'
  };

  var METHOD_TYPES = [
    { value: 'phone', name: '电话' },
    { value: 'email', name: '邮箱' },
    { value: 'wechat', name: '微信' },
    { value: 'address', name: '地址' },
    { value: 'other', name: '其他' }
  ];

  var TYPE_NAME = {};
  METHOD_TYPES.forEach(function (item) {
    TYPE_NAME[item.value] = item.name;
  });

  var ICON_PATHS = {
    phone:
      '<path d="M6.5 3h3L11 7 9 8.5a11 11 0 0 0 5 5L15.5 11l4 1.5v3a2 2 0 0 1-2.2 2A15.5 15.5 0 0 1 4.5 5.2 2 2 0 0 1 6.5 3Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    email:
      '<rect x="3" y="5" width="18" height="14" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="m4.5 7.5 7.5 5.5 7.5-5.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
    wechat:
      '<path d="M9.2 4.5C5.9 4.5 3.2 6.7 3.2 9.4c0 1.5.8 2.9 2.1 3.8l-.6 1.9 2.2-1.1c.4.1.9.1 1.4.1" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M20.8 14.1c0-2.4-2.4-4.3-5.3-4.3s-5.3 1.9-5.3 4.3 2.4 4.3 5.3 4.3c.6 0 1.2-.1 1.7-.2l1.9.9-.5-1.6c1.3-.8 2.2-2 2.2-3.4Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
    address:
      '<path d="M12 21s7-5.4 7-11a7 7 0 1 0-14 0c0 5.6 7 11 7 11Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><circle cx="12" cy="10" r="2.5" fill="none" stroke="currentColor" stroke-width="1.6"/>',
    other:
      '<circle cx="6" cy="12" r="1.7" fill="currentColor"/><circle cx="12" cy="12" r="1.7" fill="currentColor"/><circle cx="18" cy="12" r="1.7" fill="currentColor"/>',
    star:
      '<path d="m12 3.8 2.6 5.2 5.8.9-4.2 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8L3.6 9.9l5.8-.9Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    starFilled:
      '<path d="m12 3.8 2.6 5.2 5.8.9-4.2 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8L3.6 9.9l5.8-.9Z" fill="currentColor" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    close:
      '<path d="m6 6 12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/>'
  };

  var SEARCH_DEBOUNCE_MS = 300;
  var TOAST_DURATION_MS = 3200;

  /* -------------------------------------------------------------- DOM */

  var el = {
    grid: document.getElementById('contactGrid'),
    emptyState: document.getElementById('emptyState'),
    countLabel: document.getElementById('countLabel'),
    searchInput: document.getElementById('searchInput'),
    btnCreate: document.getElementById('btnCreate'),
    btnImport: document.getElementById('btnImport'),
    btnExport: document.getElementById('btnExport'),
    btnTemplate: document.getElementById('btnTemplate'),

    drawer: document.getElementById('drawer'),
    drawerTitle: document.getElementById('drawerTitle'),
    form: document.getElementById('contactForm'),
    formError: document.getElementById('formError'),
    btnSave: document.getElementById('btnSave'),
    inputName: document.getElementById('inputName'),
    inputCompany: document.getElementById('inputCompany'),
    inputNote: document.getElementById('inputNote'),
    inputFavorite: document.getElementById('inputFavorite'),
    methodList: document.getElementById('methodList'),
    btnAddMethod: document.getElementById('btnAddMethod'),

    importModal: document.getElementById('importModal'),
    importFile: document.getElementById('importFile'),
    importFileName: document.getElementById('importFileName'),
    importResult: document.getElementById('importResult'),
    btnDoImport: document.getElementById('btnDoImport'),
    btnDownloadTemplate: document.getElementById('btnDownloadTemplate'),

    confirmModal: document.getElementById('confirmModal'),
    confirmName: document.getElementById('confirmName'),
    btnConfirmDelete: document.getElementById('btnConfirmDelete'),

    toastStack: document.getElementById('toastStack')
  };

  /* -------------------------------------------------------------- 状态 */

  var state = {
    contacts: [],
    filter: 'all',
    keyword: '',
    editingId: null,
    pendingDeleteId: null,
    expanded: {},
    importing: false
  };

  var searchTimer = null;

  /* -------------------------------------------------------------- 工具 */

  function icon(name, className) {
    var path = ICON_PATHS[name] || ICON_PATHS.other;
    return (
      '<svg' +
      (className ? ' class="' + className + '"' : '') +
      ' viewBox="0 0 24 24" aria-hidden="true">' +
      path +
      '</svg>'
    );
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function initialOf(name) {
    var text = String(name || '').trim();
    return text ? text.charAt(0).toUpperCase() : '?';
  }

  function toast(message, type) {
    var node = document.createElement('div');
    node.className = 'toast toast--' + (type || 'info');
    node.textContent = message;
    el.toastStack.appendChild(node);
    window.setTimeout(function () {
      node.classList.add('is-leaving');
      window.setTimeout(function () {
        node.remove();
      }, 220);
    }, TOAST_DURATION_MS);
  }

  function withLoading(button, task) {
    if (!button) {
      return Promise.resolve().then(task);
    }
    button.classList.add('is-loading');
    button.disabled = true;
    return Promise.resolve()
      .then(task)
      .finally(function () {
        button.classList.remove('is-loading');
        button.disabled = false;
      });
  }

  function lockBody(locked) {
    document.body.style.overflow = locked ? 'hidden' : '';
  }

  /* -------------------------------------------------------------- API 层 */

  function request(url, options) {
    var config = options || {};
    return fetch(url, config).then(function (response) {
      return response
        .json()
        .catch(function () {
          throw new Error('服务器返回了无法解析的数据（HTTP ' + response.status + '）');
        })
        .then(function (payload) {
          if (!payload || payload.code !== 0) {
            var message = (payload && payload.message) || '请求失败（HTTP ' + response.status + '）';
            throw new Error(message);
          }
          return payload.data;
        });
    });
  }

  function jsonRequest(method, url, body) {
    return request(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
  }

  var api = {
    list: function (params) {
      var query = new URLSearchParams();
      if (params.favorite) {
        query.set('favorite', params.favorite);
      }
      if (params.keyword) {
        query.set('keyword', params.keyword);
      }
      var suffix = query.toString();
      return request(API.contacts + (suffix ? '?' + suffix : ''));
    },
    create: function (data) {
      return jsonRequest('POST', API.contacts, data);
    },
    update: function (id, data) {
      return jsonRequest('PUT', API.contacts + '/' + id, data);
    },
    remove: function (id) {
      return request(API.contacts + '/' + id, { method: 'DELETE' });
    },
    favorite: function (id, isFavorite) {
      return jsonRequest('POST', API.contacts + '/' + id + '/favorite', {
        isFavorite: isFavorite
      });
    },
    importFile: function (file) {
      var form = new FormData();
      form.append('file', file);
      return request(API.importUrl, { method: 'POST', body: form });
    }
  };

  /* -------------------------------------------------------------- 渲染层 */

  function renderMethods(contact) {
    var methods = contact.methods || [];
    var expanded = !!state.expanded[contact.id];
    var visible = expanded ? methods : methods.slice(0, 2);
    var parts = visible.map(function (method) {
      var label = method.label || TYPE_NAME[method.type] || '其他';
      return (
        '<div class="card__method">' +
        icon(method.type) +
        '<span class="card__method-value" title="' +
        escapeHtml(label + '：' + method.value) +
        '">' +
        escapeHtml(method.value) +
        '</span>' +
        '</div>'
      );
    });
    if (!expanded && methods.length > 2) {
      parts.push(
        '<span class="card__methods-more">还有 ' + (methods.length - 2) + ' 条联系方式</span>'
      );
    }
    return parts.join('');
  }

  function createCard(contact) {
    var card = document.createElement('article');
    card.className = 'card' + (contact.isFavorite ? ' is-favorite' : '');
    card.dataset.id = String(contact.id);

    var methods = contact.methods || [];
    var expanded = !!state.expanded[contact.id];

    card.innerHTML =
      '<div class="card__head">' +
      '<span class="card__avatar" aria-hidden="true">' + escapeHtml(initialOf(contact.name)) + '</span>' +
      '<div class="card__ident">' +
      '<h3 class="card__name" title="' + escapeHtml(contact.name) + '">' + escapeHtml(contact.name) + '</h3>' +
      '<p class="card__company">' + escapeHtml(contact.company || '未填写公司') + '</p>' +
      '</div>' +
      '<button class="star' + (contact.isFavorite ? ' is-active' : '') + '" type="button"' +
      ' aria-label="' + (contact.isFavorite ? '取消收藏' : '收藏') + '"' +
      ' aria-pressed="' + (contact.isFavorite ? 'true' : 'false') + '"' +
      ' data-action="favorite">' +
      icon(contact.isFavorite ? 'starFilled' : 'star') +
      '</button>' +
      '</div>' +
      (contact.note ? '<p class="card__note">' + escapeHtml(contact.note) + '</p>' : '') +
      '<div class="card__methods">' + renderMethods(contact) + '</div>' +
      '<div class="card__actions">' +
      '<button class="card__action" type="button" data-action="detail">' +
      (expanded ? '收起' : '查看详情') +
      '</button>' +
      '<button class="card__action" type="button" data-action="edit">编辑</button>' +
      '<button class="card__action card__action--danger" type="button" data-action="delete">删除</button>' +
      '</div>';

    void methods;
    return card;
  }

  function updateCount() {
    var total = state.contacts.length;
    var favoriteCount = state.contacts.filter(function (item) {
      return item.isFavorite;
    }).length;
    if (!total) {
      el.countLabel.textContent = state.filter === 'favorite' ? '只看收藏 · 暂无匹配' : '';
      return;
    }
    var text = '共 ' + total + ' 位联系人';
    if (state.filter === 'favorite') {
      text = '只看收藏 · ' + total + ' 位';
    } else if (favoriteCount) {
      text += ' · ' + favoriteCount + ' 位已收藏';
    }
    el.countLabel.textContent = text;
  }

  function render() {
    el.grid.innerHTML = '';
    state.contacts.forEach(function (contact) {
      el.grid.appendChild(createCard(contact));
    });
    var isEmpty = state.contacts.length === 0;
    el.emptyState.hidden = !isEmpty;
    el.grid.hidden = isEmpty;
    updateCount();
  }

  function loadContacts() {
    el.grid.setAttribute('aria-busy', 'true');
    var params = {
      favorite: state.filter === 'favorite' ? '1' : '',
      keyword: state.keyword
    };
    return api
      .list(params)
      .then(function (data) {
        state.contacts = Array.isArray(data) ? data : [];
        render();
      })
      .catch(function (error) {
        toast(error.message, 'error');
      })
      .finally(function () {
        el.grid.setAttribute('aria-busy', 'false');
      });
  }

  /* -------------------------------------------------------------- 抽屉 */

  function showFormError(message) {
    el.formError.textContent = message;
    el.formError.hidden = false;
  }

  function hideFormError() {
    el.formError.hidden = true;
    el.formError.textContent = '';
  }

  function addMethodRow(method) {
    var data = method || { type: 'phone', label: '', value: '' };
    var row = document.createElement('div');
    row.className = 'method-row';

    var options = METHOD_TYPES.map(function (item) {
      var selected = item.value === data.type ? ' selected' : '';
      return '<option value="' + item.value + '"' + selected + '>' + item.name + '</option>';
    }).join('');

    row.innerHTML =
      '<select class="input method-row__type" aria-label="联系方式类型">' + options + '</select>' +
      '<input class="input method-row__label" type="text" maxlength="40" placeholder="备注（可空）"' +
      ' aria-label="联系方式备注" value="' + escapeHtml(data.label || '') + '">' +
      '<input class="input method-row__value" type="text" maxlength="200" placeholder="值"' +
      ' aria-label="联系方式的值" value="' + escapeHtml(data.value || '') + '">' +
      '<button class="icon-btn method-row__remove" type="button" aria-label="删除该行">' +
      icon('close') +
      '</button>';

    row.querySelector('.method-row__remove').addEventListener('click', function () {
      row.remove();
    });

    el.methodList.appendChild(row);
  }

  function openDrawer(contact) {
    state.editingId = contact ? contact.id : null;
    el.drawerTitle.textContent = contact ? '编辑联系人' : '新增联系人';
    el.inputName.value = contact ? contact.name : '';
    el.inputCompany.value = contact ? contact.company || '' : '';
    el.inputNote.value = contact ? contact.note || '' : '';
    el.inputFavorite.checked = contact ? !!contact.isFavorite : false;

    el.methodList.innerHTML = '';
    var methods = contact && contact.methods && contact.methods.length
      ? contact.methods
      : [{ type: 'phone', label: '', value: '' }];
    methods.forEach(function (method) {
      addMethodRow(method);
    });

    hideFormError();
    el.drawer.hidden = false;
    lockBody(true);
    window.setTimeout(function () {
      el.inputName.focus();
    }, 60);
  }

  function closeDrawer() {
    el.drawer.hidden = true;
    state.editingId = null;
    lockBody(false);
  }

  function collectForm() {
    var name = el.inputName.value.trim();
    if (!name) {
      return { error: '请填写姓名' };
    }

    var rows = Array.prototype.slice.call(
      el.methodList.querySelectorAll('.method-row')
    );
    var methods = [];
    rows.forEach(function (row) {
      var value = row.querySelector('.method-row__value').value.trim();
      if (!value) {
        return;
      }
      methods.push({
        type: row.querySelector('.method-row__type').value,
        label: row.querySelector('.method-row__label').value.trim(),
        value: value
      });
    });

    if (!methods.length) {
      return { error: '请至少填写一条联系方式的值' };
    }

    return {
      data: {
        name: name,
        company: el.inputCompany.value.trim(),
        note: el.inputNote.value.trim(),
        isFavorite: el.inputFavorite.checked,
        methods: methods
      }
    };
  }

  /* -------------------------------------------------------------- 事件层 */

  function onGridClick(event) {
    var button = event.target.closest('[data-action]');
    if (!button) {
      return;
    }
    var card = event.target.closest('.card');
    if (!card) {
      return;
    }
    var contactId = Number(card.dataset.id);
    var contact = state.contacts.filter(function (item) {
      return item.id === contactId;
    })[0];
    if (!contact) {
      return;
    }

    var action = button.dataset.action;

    if (action === 'favorite') {
      toggleFavorite(contact, button);
      return;
    }

    if (action === 'detail') {
      state.expanded[contactId] = !state.expanded[contactId];
      card.replaceWith(createCard(contact));
      return;
    }

    if (action === 'edit') {
      openDrawer(contact);
      return;
    }

    if (action === 'delete') {
      state.pendingDeleteId = contactId;
      el.confirmName.textContent = contact.name;
      el.confirmModal.hidden = false;
      lockBody(true);
    }
  }

  function toggleFavorite(contact, button) {
    var next = !contact.isFavorite;
    var previous = contact.isFavorite;

    contact.isFavorite = next;
    button.classList.toggle('is-active', next);
    button.setAttribute('aria-pressed', next ? 'true' : 'false');
    button.setAttribute('aria-label', next ? '取消收藏' : '收藏');
    button.innerHTML = icon(next ? 'starFilled' : 'star');
    button.closest('.card').classList.toggle('is-favorite', next);

    api
      .favorite(contact.id, next)
      .then(function () {
        toast(next ? '已加入收藏' : '已取消收藏', 'success');
        return loadContacts();
      })
      .catch(function (error) {
        contact.isFavorite = previous;
        toast(error.message, 'error');
        return loadContacts();
      });
  }

  function submitForm(event) {
    event.preventDefault();
    hideFormError();

    var result = collectForm();
    if (result.error) {
      showFormError(result.error);
      return;
    }

    var editingId = state.editingId;
    withLoading(el.btnSave, function () {
      var task = editingId ? api.update(editingId, result.data) : api.create(result.data);
      return task
        .then(function () {
          closeDrawer();
          toast(editingId ? '修改已保存' : '联系人已新增', 'success');
          return loadContacts();
        })
        .catch(function (error) {
          showFormError(error.message);
        });
    });
  }

  function confirmDelete() {
    var contactId = state.pendingDeleteId;
    if (!contactId) {
      return;
    }
    withLoading(el.btnConfirmDelete, function () {
      return api
        .remove(contactId)
        .then(function () {
          el.confirmModal.hidden = true;
          state.pendingDeleteId = null;
          lockBody(false);
          toast('已删除该联系人', 'success');
          return loadContacts();
        })
        .catch(function (error) {
          toast(error.message, 'error');
        });
    });
  }

  function handleSearch() {
    state.keyword = el.searchInput.value.trim();
    loadContacts();
  }

  function onSearchInput() {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(handleSearch, SEARCH_DEBOUNCE_MS);
  }

  function onSearchKeydown(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      window.clearTimeout(searchTimer);
      handleSearch();
    }
  }

  function setFilter(filter) {
    if (state.filter === filter) {
      return;
    }
    state.filter = filter;
    Array.prototype.forEach.call(
      document.querySelectorAll('.segmented__item'),
      function (button) {
        var active = button.dataset.filter === filter;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
      }
    );
    loadContacts();
  }

  function openImportModal() {
    el.importFile.value = '';
    el.importFileName.textContent = '点击选择 .xlsx 文件';
    el.importResult.hidden = true;
    el.importResult.className = 'import-result';
    el.importResult.innerHTML = '';
    el.importModal.hidden = false;
    lockBody(true);
  }

  function closeImportModal() {
    el.importModal.hidden = true;
    lockBody(false);
  }

  function renderImportResult(result) {
    var errors = result.errors || [];
    var tone = errors.length ? 'warning' : 'success';
    var html =
      '<p class="import-result__title">成功新增 ' +
      result.inserted +
      ' 条，跳过 ' +
      result.skipped +
      ' 条</p>' +
      '<p>共发现 ' +
      errors.length +
      ' 个问题' +
      (errors.length ? '，明细如下：' : '。') +
      '</p>';
    if (errors.length) {
      html +=
        '<ul class="import-result__list">' +
        errors
          .map(function (item) {
            return '<li>' + escapeHtml(item) + '</li>';
          })
          .join('') +
        '</ul>';
    }
    el.importResult.className = 'import-result import-result--' + tone;
    el.importResult.innerHTML = html;
    el.importResult.hidden = false;
  }

  function doImport() {
    var file = el.importFile.files && el.importFile.files[0];
    if (!file) {
      toast('请先选择要导入的 .xlsx 文件', 'warning');
      return;
    }
    if (!/\.xlsx$/i.test(file.name)) {
      toast('只支持 .xlsx 文件', 'warning');
      return;
    }

    state.importing = true;
    withLoading(el.btnDoImport, function () {
      return api
        .importFile(file)
        .then(function (result) {
          renderImportResult(result);
          if (result.inserted > 0) {
            toast('导入完成，新增 ' + result.inserted + ' 条', 'success');
            loadContacts();
          } else {
            toast('没有导入任何联系人', 'warning');
          }
        })
        .catch(function (error) {
          el.importResult.className = 'import-result import-result--error';
          el.importResult.innerHTML =
            '<p class="import-result__title">导入失败</p><p>' + escapeHtml(error.message) + '</p>';
          el.importResult.hidden = false;
          toast(error.message, 'error');
        })
        .finally(function () {
          state.importing = false;
        });
    });
  }

  function download(url) {
    window.location.href = url;
  }

  function onKeydown(event) {
    if (event.key !== 'Escape') {
      return;
    }
    if (!el.drawer.hidden) {
      closeDrawer();
      return;
    }
    if (!el.importModal.hidden) {
      closeImportModal();
      return;
    }
    if (!el.confirmModal.hidden) {
      el.confirmModal.hidden = true;
      state.pendingDeleteId = null;
      lockBody(false);
    }
  }

  /* -------------------------------------------------------------- 绑定 */

  function bindEvents() {
    el.grid.addEventListener('click', onGridClick);
    el.btnCreate.addEventListener('click', function () {
      openDrawer(null);
    });
    el.form.addEventListener('submit', submitForm);
    el.btnAddMethod.addEventListener('click', function () {
      addMethodRow(null);
    });

    el.searchInput.addEventListener('input', onSearchInput);
    el.searchInput.addEventListener('keydown', onSearchKeydown);

    Array.prototype.forEach.call(
      document.querySelectorAll('.segmented__item'),
      function (button) {
        button.addEventListener('click', function () {
          setFilter(button.dataset.filter);
        });
      }
    );

    el.btnExport.addEventListener('click', function () {
      download(API.exportUrl);
      toast('正在生成 Excel 文件…', 'info');
    });
    el.btnTemplate.addEventListener('click', function () {
      download(API.templateUrl);
    });

    el.btnImport.addEventListener('click', openImportModal);
    el.btnDownloadTemplate.addEventListener('click', function () {
      download(API.templateUrl);
    });
    el.btnDoImport.addEventListener('click', doImport);

    el.importFile.addEventListener('change', function () {
      var file = el.importFile.files && el.importFile.files[0];
      el.importFileName.textContent = file ? file.name : '点击选择 .xlsx 文件';
    });

    Array.prototype.forEach.call(
      document.querySelectorAll('[data-close-drawer]'),
      function (node) {
        node.addEventListener('click', closeDrawer);
      }
    );
    Array.prototype.forEach.call(
      document.querySelectorAll('[data-close-import]'),
      function (node) {
        node.addEventListener('click', closeImportModal);
      }
    );
    Array.prototype.forEach.call(
      document.querySelectorAll('[data-close-confirm]'),
      function (node) {
        node.addEventListener('click', function () {
          el.confirmModal.hidden = true;
          state.pendingDeleteId = null;
          lockBody(false);
        });
      }
    );

    el.btnConfirmDelete.addEventListener('click', confirmDelete);
    document.addEventListener('keydown', onKeydown);
  }

  /* -------------------------------------------------------------- 启动 */

  bindEvents();
  addMethodRow(null);
  loadContacts();
})();
