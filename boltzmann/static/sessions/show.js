const JOBS = new Map()
const ROWS = new Map()
const CIFS = new Map()

let CURRENT_JOB_ID   = null
let CURRENT_MODEL_ID = null

function sync_jobs(jobs) {
  const job_list = document.getElementById('job-list')

  for (const [id, info] of Object.entries(jobs)) {
    const oldinfo = JOBS.get(id)
    if(oldinfo && oldinfo.docking == info.docking && oldinfo.scoring == info.scoring) {
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
    element.querySelector('.score').innerText   = info.boltz_ptm || ''
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

async function pull_model(job_id, model_id) {
  const modelurl = `/api/v1/${window.location.pathname}/jobs/${job_id}/models/${model_id}`
  const response = await fetch(modelurl)
  if(!response.ok) return;

  CIFS.set(`${job_id}:${model_id}`, await response.text())
  show_model(job_id, model_id)
}

function show_model(job_id, model_id) {
  const cif = CIFS.get(`${job_id}:${model_id}`)
  if(cif) {
    viewer.removeAllModels()
    viewer.addModel(cif, 'cif')

    // Style the protein...
    apply_style("A", STYLE[JOBS.get(job_id).protein])

    // Style the ligand...
    viewer.setStyle({chain: "B"}, {stick: {}})

    // And show it!
    viewer.zoomTo({chain: "B"})
    viewer.render()
  }
  else {
    pull_model(job_id, model_id)
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
  enqueue([{
    protein_id: protein_select.value,
    name:       'Mol' + JOBS.size,
    smiles:     editor.smiles()
  }])

  close_modal()
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

    const jobs = job_list.children
    for(let i = 0; i < jobs.length; ++i) {
      const job = jobs[i]
      job.classList.toggle('active', job === target)
    }

    // CURRENT_MODEL_ID = 0
    CURRENT_JOB_ID = target.dataset.job_id
    show_model(CURRENT_JOB_ID, CURRENT_MODEL_ID)
    // show_demo()
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


// Load SMILES into the JSME editor:
// editor.readGenericMolecularInput(smiles)

// Get SMILES out of the JSME editor:
// let smiles = editor.smiles()

function jsmeOnLoad() {
  editor = new JSApplet.JSME('editor', '600px', '440px', {
    'options': 'hydrogens,fullScreenIcon',
  })
}

const element = document.getElementById('viewer')
const viewer  = $3Dmol.createViewer(element, {background: '#fff'});
// viewer.addModel('url:/static/test.cif', 'cif')

// Add a new color scheme that preserves all defaults except carbon:
const colors = {...$3Dmol.elementColors.rasmol, C: '#486860'}
$3Dmol.builtinColorSchemes['residue'] = {prop: 'elem', map: colors}

function apply_style(chain, style) {
  for(const rule of style) {
    query = {...rule.query, chain: chain}
    viewer.setStyle(query, rule.style)
  }
}

async function show_demo() {
  viewer.removeAllModels()
  const response = await fetch('/static/test.cif')
  viewer.addModel(await response.text(), 'cif')

  // viewer.setStyle({chain:"A"},                 {cartoon:{color:"#9dc"}})
  // viewer.setStyle({chain:"A", resi:"11-18"},   {cartoon:{color:"#9dc"}, stick:{colorscheme:colors, radius:0.1}})
  // viewer.setStyle({chain:"A", resi:"84-94"},   {cartoon:{color:"#9dc"}, stick:{colorscheme:colors, radius:0.1}})
  // viewer.setStyle({chain:"A", resi:"147-150"}, {cartoon:{color:"#9dc"}, stick:{colorscheme:colors, radius:0.1}})

  apply_style('A', STYLE['NLK'])

  viewer.setStyle({chain: 'B'}, {stick: {}})
  viewer.zoomTo({chain: 'B'})
  viewer.render()
}



async function poll_jobs() {
  const response = await fetch(API)
  sync_jobs(await response.json())
}

setInterval(poll_jobs, 60000)
poll_jobs()
