document.documentElement.classList.add('js');

const menuButton = document.querySelector('[data-menu]');
const navigation = document.querySelector('[data-nav]');

function setMenu(open) {
  if (!menuButton || !navigation) return;
  navigation.classList.toggle('is-open', open);
  menuButton.setAttribute('aria-expanded', String(open));
}

menuButton?.addEventListener('click', () => {
  setMenu(!navigation?.classList.contains('is-open'));
});

navigation?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => setMenu(false));
});

addEventListener('keydown', (event) => {
  if (event.key === 'Escape') setMenu(false);
});

const intakeForm = document.querySelector('[data-intake-form]');
const copyIntakeButton = document.querySelector('[data-copy-intake]');
const intakeStatus = document.querySelector('[data-intake-status]');
const intakeRecipient = 'Lucapanay13@gmail.com';
const intakeSubject = 'AI Agent Reliability Audit enquiry';
const maxMailtoLength = 1900;
const intakeQuestions = [
  ['purpose', 'Workflow purpose'],
  ['systems', 'Tools or systems changed'],
  ['done', 'What currently counts as done'],
  ['uncertainty', 'Known failure or uncertainty'],
  ['evidence', 'Representative or redacted evidence available'],
];

function intakeText() {
  if (!intakeForm) return '';
  const data = new FormData(intakeForm);
  return intakeQuestions
    .map(([name, label]) => `${label}:\n${String(data.get(name) || '').trim()}`)
    .join('\n\n');
}

function intakeIsValid() {
  if (!intakeForm) return false;
  const valid = intakeForm.reportValidity();
  if (!valid && intakeStatus) {
    intakeStatus.textContent = 'Complete all five fields and confirm the privacy boundary.';
  }
  return valid;
}

intakeForm?.addEventListener('submit', (event) => {
  event.preventDefault();
  if (!intakeIsValid()) return;
  const body = intakeText();
  const href = `mailto:${intakeRecipient}?subject=${encodeURIComponent(intakeSubject)}&body=${encodeURIComponent(body)}`;
  if (href.length > maxMailtoLength) {
    if (intakeStatus) {
      intakeStatus.textContent = 'This enquiry is too long for a reliable email draft. Use “Copy enquiry” instead.';
    }
    return;
  }
  if (intakeStatus) {
    intakeStatus.textContent = 'Opening an email draft. Review the contents before sending.';
  }
  window.location.href = href;
});

copyIntakeButton?.addEventListener('click', async () => {
  if (!intakeIsValid()) return;
  if (!navigator.clipboard?.writeText) {
    if (intakeStatus) {
      intakeStatus.textContent = 'Clipboard access is unavailable here. Use “Open email draft” instead.';
    }
    return;
  }
  try {
    await navigator.clipboard.writeText(intakeText());
    if (intakeStatus) {
      intakeStatus.textContent = 'Enquiry copied. Review it before pasting or sending.';
    }
  } catch {
    if (intakeStatus) {
      intakeStatus.textContent = 'The browser blocked clipboard access. Use “Open email draft” instead.';
    }
  }
});
