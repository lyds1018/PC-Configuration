(function () {
    function openRejectDialog(options) {
        const title = options.title || '驳回帖子';
        const postTitle = options.postTitle || '';

        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'pc-modal-overlay';

            const dialog = document.createElement('div');
            dialog.className = 'pc-modal';
            dialog.setAttribute('role', 'dialog');
            dialog.setAttribute('aria-modal', 'true');

            const titleEl = document.createElement('div');
            titleEl.className = 'pc-modal-title';
            titleEl.textContent = title;
            dialog.appendChild(titleEl);

            if (postTitle) {
                const messageEl = document.createElement('div');
                messageEl.className = 'pc-modal-message';
                messageEl.textContent = `帖子：${postTitle}`;
                dialog.appendChild(messageEl);
            }

            const input = document.createElement('input');
            input.type = 'text';
            input.maxLength = 255;
            input.placeholder = '驳回原因';
            input.className = 'form-control pc-modal-input';
            dialog.appendChild(input);

            const checkWrap = document.createElement('label');
            checkWrap.className = 'forum-ban-check mt-1';
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = '1';
            checkWrap.appendChild(checkbox);
            checkWrap.appendChild(document.createTextNode('封禁该用户'));
            dialog.appendChild(checkWrap);

            const actions = document.createElement('div');
            actions.className = 'pc-modal-actions';
            const cancelBtn = document.createElement('button');
            cancelBtn.type = 'button';
            cancelBtn.className = 'btn btn-outline';
            cancelBtn.textContent = '取消';
            const rejectBtn = document.createElement('button');
            rejectBtn.type = 'button';
            rejectBtn.className = 'btn btn-primary';
            rejectBtn.textContent = '确认驳回';
            actions.appendChild(cancelBtn);
            actions.appendChild(rejectBtn);
            dialog.appendChild(actions);

            overlay.appendChild(dialog);
            document.body.appendChild(overlay);

            const cleanup = () => {
                document.removeEventListener('keydown', onKeydown);
                overlay.remove();
            };
            const cancel = () => {
                cleanup();
                resolve({ confirmed: false, reason: '', banUser: false });
            };
            const confirm = () => {
                cleanup();
                resolve({
                    confirmed: true,
                    reason: (input.value || '').trim(),
                    banUser: checkbox.checked,
                });
            };
            const onKeydown = (event) => {
                if (event.key === 'Escape') {
                    event.preventDefault();
                    cancel();
                } else if (event.key === 'Enter') {
                    event.preventDefault();
                    confirm();
                }
            };

            cancelBtn.addEventListener('click', cancel);
            rejectBtn.addEventListener('click', confirm);
            overlay.addEventListener('click', (event) => {
                if (event.target === overlay) cancel();
            });
            document.addEventListener('keydown', onKeydown);
            input.focus();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        const triggers = document.querySelectorAll('.js-forum-reject-trigger');
        if (!triggers.length) return;

        triggers.forEach((trigger) => {
            trigger.addEventListener('click', async function () {
                const postId = trigger.getAttribute('data-post-id');
                if (!postId) return;
                const form = document.getElementById(`forum-reject-form-${postId}`);
                if (!form) return;

                const result = await openRejectDialog({
                    title: '驳回帖子',
                    postTitle: trigger.getAttribute('data-post-title') || '',
                });
                if (!result.confirmed) return;

                const reasonInput = form.querySelector('input[name="reject_reason"]');
                const banInput = form.querySelector('input[name="ban_user"]');
                if (reasonInput) reasonInput.value = result.reason;
                if (banInput) banInput.value = result.banUser ? '1' : '0';
                form.submit();
            });
        });
    });
})();
