(function () {
    function openReplyDialog(replyUser) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'pc-modal-overlay';

            const dialog = document.createElement('div');
            dialog.className = 'pc-modal';
            dialog.setAttribute('role', 'dialog');
            dialog.setAttribute('aria-modal', 'true');

            const titleEl = document.createElement('div');
            titleEl.className = 'pc-modal-title';
            titleEl.textContent = '回复评论';
            dialog.appendChild(titleEl);

            const messageEl = document.createElement('div');
            messageEl.className = 'pc-modal-message';
            messageEl.textContent = `回复 ${replyUser || '该用户'}`;
            dialog.appendChild(messageEl);

            const textarea = document.createElement('textarea');
            textarea.className = 'form-control pc-modal-input';
            textarea.rows = 4;
            textarea.placeholder = '请输入回复内容';
            dialog.appendChild(textarea);

            const actions = document.createElement('div');
            actions.className = 'pc-modal-actions';

            const cancelBtn = document.createElement('button');
            cancelBtn.type = 'button';
            cancelBtn.className = 'btn btn-outline';
            cancelBtn.textContent = '取消';

            const submitBtn = document.createElement('button');
            submitBtn.type = 'button';
            submitBtn.className = 'btn btn-primary';
            submitBtn.textContent = '回复';

            actions.appendChild(cancelBtn);
            actions.appendChild(submitBtn);
            dialog.appendChild(actions);
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);

            const cleanup = () => {
                document.removeEventListener('keydown', onKeydown);
                overlay.remove();
            };
            const cancel = () => {
                cleanup();
                resolve({ confirmed: false, content: '' });
            };
            const confirm = () => {
                const content = (textarea.value || '').trim();
                if (!content) {
                    if (window.PCConfig && typeof window.PCConfig.showNotification === 'function') {
                        window.PCConfig.showNotification('回复内容不能为空。', 'warning');
                    }
                    textarea.focus();
                    return;
                }
                cleanup();
                resolve({ confirmed: true, content });
            };
            const onKeydown = (event) => {
                if (event.key === 'Escape') {
                    event.preventDefault();
                    cancel();
                }
            };

            cancelBtn.addEventListener('click', cancel);
            submitBtn.addEventListener('click', confirm);
            overlay.addEventListener('click', (event) => {
                if (event.target === overlay) cancel();
            });
            document.addEventListener('keydown', onKeydown);
            textarea.focus();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        const triggers = document.querySelectorAll('.js-comment-reply-target');
        const form = document.getElementById('forum-modal-reply-form');
        if (!triggers.length || !form) return;

        const parentInput = form.querySelector('input[name="parent_id"]');
        const contentInput = form.querySelector('input[name="content"]');
        if (!parentInput || !contentInput) return;

        triggers.forEach((trigger) => {
            trigger.addEventListener('click', async function () {
                const parentId = trigger.getAttribute('data-parent-id');
                const replyUser = trigger.getAttribute('data-reply-user') || '';
                if (!parentId) return;

                const result = await openReplyDialog(replyUser);
                if (!result.confirmed) return;

                parentInput.value = parentId;
                contentInput.value = result.content;
                form.submit();
            });
        });
    });
})();
