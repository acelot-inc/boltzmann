const JOBS = new Map()
const ROWS = new Map()
const CIFS = new Map()
const VIEW = new Map()

let CURRENT_JOB_ID   = undefined
let CURRENT_MODEL_ID = undefined

function ordinal(number) {
  const tens = number % 100
  const ones = number % 10

  if(tens > 10 && tens < 20) {
    return number + 'th'
  }
  else if(ones === 1) {
    return number + 'st'
  }
  else if(ones === 2) {
    return number + 'nd'
  }
  else if(ones === 3) {
    return number + 'rd'
  }
  else {
    return number + 'th'
  }
}

function get_status(job) {
  if(job.docking === 'pending') {
    if(job.place) {
      return 'docking ' + ordinal(job.place)
    }
    else {
      return 'docking pending'
    }
  }
  else if(job.docking === 'running') {
    return 'docking running'
  }
  else if(job.docking === 'failed') {
    return 'docking failed'
  }
  else {
    if(job.scoring === 'pending') {
      if(job.place) {
      return 'scoring' + ordinal(job.place)
    }
    else {
      return 'scoring pending'
    }
    }
    else if(job.scoring === 'running') {
      return 'scoring running'
    }
    else if(job.scoring === 'failed') {
      return 'scoring failed'
    }
    else {
      let lowest = job.scores[0].vina_score
      for(let i = 1; i < job.scores.length; ++i) {
        lowest = Math.min(lowest, job.scores[i].vina_score)
      }

      return 'finished ' + lowest.toFixed(1)
    }
  }
}

function sync_jobs(data) {
  if(data.queues) {
    document.getElementById('docking-queue-depth').innerText = data.queues.docking
    document.getElementById('scoring-queue-depth').innerText = data.queues.scoring
  }

  const job_list = document.getElementById('job-list')

  for (const [id, info] of Object.entries(data.jobs)) {
    const oldinfo = JOBS.get(id)
    if(oldinfo && info.place && info.place !== oldinfo.place) {
      // Needs an update...
    }
    else if(oldinfo && oldinfo.docking == info.docking && oldinfo.scoring == info.scoring) {
      // Already up to date...
      continue
    }

    let element = ROWS.get(id)
    if(!element) {
      const template = document.getElementById('job-template')
      element = template.content.firstElementChild.cloneNode(true)

      job_list.appendChild(element)
      ROWS.set(id, element)
    }

    // Update element!
    element.dataset.job_id = info.id
    element.dataset.smiles = info.smiles
    element.querySelector('.name').innerText    = info.name || '???'
    element.querySelector('.protein').innerText = info.protein || '???'
    element.querySelector('.score').innerText   = get_status(info)
    element.classList.toggle('clickable', info.docking === 'finished')

    JOBS.set(id, info)

    const canvas = element.querySelector('canvas')
    // canvas.setAttribute('id', `job${info.id}-canvas`)

    const drawer = new SmilesDrawer.Drawer({
      width:  canvas.clientWidth,
      height: canvas.clientHeight,
    })

    SmilesDrawer.parse(info.smiles, function(tree) {
      // console.log(`Drawing ${info.smiles}...`)
      try {
        drawer.draw(tree, canvas, "light", false)
      }
      catch(error) {
        console.log(error)
      }
    })
  }
}

async function enqueue(request_data) {
  const response  = await fetch(API, {
    method: "POST",
    body: JSON.stringify(request_data),
    headers: {
      "Content-Type": "application/json"
    }
  })

  if(!response.ok) {
    throw new Error(`Response status: ${response.status}`)
  }

  sync_jobs(await response.json())
}

async function pull_demo(job_id, model_id) {
  const response = await fetch('/static/test.cif')
  if(!response.ok) return;

  CIFS.set(`${job_id}:${model_id}`, await response.text())
  show_model(job_id, model_id)
}

async function pull_model(job_id, model_id) {
  const modelurl = `${API}/${job_id}/models/${model_id}`
  const response = await fetch(modelurl)
  if(!response.ok) return;

  CIFS.set(`${job_id}:${model_id}`, await response.text())
  show_model(job_id, model_id)
}

function show_model(job_id, model_id) {
  const model = CIFS.get(`${job_id}:${model_id}`)
  if(model) {
    viewer.removeAllModels()
    viewer.addModel(model, 'pdb')

    // Style the protein...
    apply_style("A", STYLE[JOBS.get(job_id).protein])

    // Style the ligand...
    viewer.setStyle({chain: "B"}, {stick: {}})

    // And show it!
    load_view_or_zoom()
    viewer.render()
  }
  else {
    pull_model(job_id, model_id)
    // pull_demo(job_id, model_id)
  }
}

function open_modal(id) {
  const screen = document.getElementById('screen')
  const modals = document.getElementById('modals').children

  for(let i = 0; i < modals.length; ++i) {
    const modal = modals[i]
    modal.classList.toggle('active', modal.id === id)
  }

  screen.style.display = 'block'
}

function close_modal() {
  const screen = document.getElementById('screen')
  const modals = document.getElementById('modals').children

  for(let i = 0; i < modals.length; ++i) {
    const modal = modals[i]
    modal.classList.remove('active')
  }

  screen.style.display = 'none'
}

function load_view_or_zoom() {
  const view = VIEW.get(CURRENT_JOB_ID)
  if(view === undefined) {
    viewer.zoomTo({chain: "B"})
  }
  else {
    viewer.setView(view)
    viewer.center({chain: "B"})
  }
}

function save_view(view) {
  if(CURRENT_JOB_ID !== undefined) {
    VIEW.set(CURRENT_JOB_ID, view)
  }
}

document.getElementById('single-job-open').addEventListener('click', event => {
  event.preventDefault()
  open_modal('single-job-modal')
})

document.getElementById('single-job-close').addEventListener('click', event => {
  event.preventDefault()
  close_modal()
})

document.getElementById('single-job-form').addEventListener('submit', event => {
  // event.stopPropagation()
  event.preventDefault()
  // console.log(event)

  const protein_select = event.target.querySelector('select[name=protein_id]')
  const custom_name    = event.target.querySelector('input[name=name]')

  let protein_id = protein_select.value
  let name       = 'Mol' + (JOBS.size + 1)

  if(custom_name.value) {
    // Unset to prevent accidental duplicates:
    name = custom_name.value
    custom_name.value = ''
  }

  enqueue([{
    protein_id: protein_id,
    name:       name,
    smiles:     editor.smiles()
  }])

  close_modal()
})

document.getElementById('download-smi-file').addEventListener('click', event => {
  // event.preventDefault()

  let smi = ''
  JOBS.forEach(job => {
    smi += `${job.smiles} ${job.name}\n`
  })

  const blob = new Blob([smi], {type: 'chemical/x-daylight-smiles'})
  event.target.href = URL.createObjectURL(blob)
})


function nearest(element, selector) {
  while(element) {
    if(element.matches(selector)) {
      return element
    }

    element = element.parentElement
  }
}


const job_list = document.getElementById('job-list')
job_list.addEventListener('click', event => {
  const target = nearest(event.target, '.job')
  if(target) {
    event.preventDefault()

    if(event.target.getAttribute('href') === '#re-enqueue') {
      const smiles = target.dataset.smiles
      editor.readGenericMolecularInput(smiles)
      open_modal('single-job-modal')
    }
    else if(event.target.getAttribute('href') === '#copy-smiles') {
      const smiles = target.dataset.smiles
      navigator.clipboard.writeText(smiles)
    }
    else if(target.classList.contains('clickable')) {
      const jobs = job_list.children
      for(let i = 0; i < jobs.length; ++i) {
        const job = jobs[i]
        job.classList.toggle('active', job === target)
      }

      CURRENT_MODEL_ID = '0'
      CURRENT_JOB_ID = target.dataset.job_id
      show_model(CURRENT_JOB_ID, CURRENT_MODEL_ID)
    }
  }
})

const models = document.getElementById('models')
models.addEventListener('click', event => {
  if(event.target.tagName === 'A') {
    event.preventDefault()

    const links = models.children
    for(let i = 0; i < links.length; ++i) {
      const link = links[i]
      link.classList.toggle('active', link === event.target)
    }

    CURRENT_MODEL_ID = event.target.getAttribute('href').slice(7)
    show_model(CURRENT_JOB_ID, CURRENT_MODEL_ID)
  }
})

function jsmeOnLoad() {
  editor = new JSApplet.JSME('editor', '600px', '440px', {
    'options': 'hydrogens,fullScreenIcon',
  })
}

const element = document.getElementById('viewer')
const viewer  = $3Dmol.createViewer(element, {background: '#fff'})
viewer.setViewChangeCallback(save_view)

// Add a new color scheme that preserves all defaults except carbon:
const colors = {...$3Dmol.elementColors.rasmol, C: '#486860'}
$3Dmol.builtinColorSchemes['residue'] = {prop: 'elem', map: colors}

function apply_style(chain, style) {
  for(const rule of style) {
    query = {...rule.query, chain: chain}
    viewer.setStyle(query, rule.style)
  }
}

async function poll_jobs() {
  const response = await fetch(API)
  sync_jobs(await response.json())
}

setInterval(poll_jobs, 60000)
poll_jobs()
