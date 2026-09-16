const content = document.getElementById('game-content');
const stepLabel = document.getElementById('step-label');
let answers = [];

async function update() {
  content.innerHTML = '<p style="margin-top:34px">Thinking…</p>';
  try {
    const response = await fetch('/api/state', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({answers})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Something went wrong');
    render(data);
  } catch (error) {
    content.textContent = `Could not load the next question: ${error.message}`;
  }
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function restart() { answers = []; update(); }

function confidenceStripe(confidence) {
  const percent = confidence * 100;
  const level = percent >= 70 ? 'high' : percent >= 35 ? 'medium' : 'low';
  const wrapper = element('div', `confidence confidence-${level}`);
  const heading = element('div', 'confidence-heading');
  heading.append(element('span', '', 'CURRENT CONFIDENCE'));
  heading.append(element('strong', '', `${percent.toFixed(1)}%`));
  const meter = element('div', 'meter');
  meter.setAttribute('role', 'progressbar');
  meter.setAttribute('aria-label', 'Confidence in the leading distro');
  meter.setAttribute('aria-valuemin', '0');
  meter.setAttribute('aria-valuemax', '100');
  meter.setAttribute('aria-valuenow', percent.toFixed(1));
  const fill = element('span');
  fill.style.width = `${Math.max(2, percent)}%`;
  meter.append(fill);
  wrapper.append(heading, meter);
  return wrapper;
}

function render(data) {
  content.replaceChildren();
  if (data.done) {
    stepLabel.textContent = data.unknown ? 'NO CONFIDENT MATCH' : data.certain ? 'I HAVE A GUESS' : 'QUESTIONS COMPLETE';
    content.append(element('div', 'result-kicker', data.unknown ? 'I could not find a confident match' : data.certain ? `I’m ${(data.confidence * 100).toFixed(1)}% confident` : 'My best guess is'));
    content.append(element('h2', 'result-name', data.unknown ? "Looks like we still don't have that distro in our database." : data.leader));
    content.append(element('p', '', data.unknown ? 'Try another distro, or play again with different answers.' : data.certain ? 'Was I right?' : `I only reached ${(data.confidence * 100).toFixed(1)}% confidence, so take this as my closest match.`));
    content.append(confidenceStripe(data.confidence));
    if (!data.unknown) {
      const others = data.top.slice(1).map(item => `${item.name} (${(item.probability * 100).toFixed(1)}%)`).join(' · ');
      content.append(element('div', 'runner-ups', `Other possibilities: ${others}`));
    }
    const again = element('button', 'primary', 'Play again ↗');
    again.addEventListener('click', restart);
    content.append(again);
    return;
  }
  stepLabel.textContent = `QUESTION ${String(data.count + 1).padStart(2, '0')} OF 30 / ${data.total_distros} POSSIBLE DISTROS`;
  content.append(element('h2', '', data.question.text));
  content.append(element('p', '', 'Answer for the distro you have in mind. Unsure? That’s fine too.'));
  content.append(confidenceStripe(data.confidence));
  const controls = element('div', 'answers');
  for (const [value, caption] of [['yes', 'Yes'], ['no', 'No'], ['unknown', 'Don’t know']]) {
    const button = element('button', `answer ${value}`, caption);
    button.type = 'button';
    button.addEventListener('click', () => {
      answers.push({question: data.question.id, answer: value});
      update();
    });
    controls.append(button);
  }
  content.append(controls);
  if (answers.length) {
    const back = element('button', 'secondary', '← Undo last answer');
    back.addEventListener('click', () => { answers.pop(); update(); });
    content.append(back);
  }
}

document.getElementById('start-button').addEventListener('click', restart);
fetch('/api/state', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({answers: []})
}).then(response => response.json()).then(data => {
  if (data.total_distros) {
    document.getElementById('intro-count').textContent = data.total_distros;
    document.getElementById('distro-count').textContent = data.total_distros;
  }
}).catch(() => {});
