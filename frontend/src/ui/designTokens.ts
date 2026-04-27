export const uiLayoutTokens = {
  drawerSize: '75%',
  gridGutter: 20,
  dialogWidth: '760px',
  formLabelWidth: '120px',
} as const

export const uiTableTokens = {
  providers: {
    nameMinWidth: 140,
    displayNameMinWidth: 180,
    typeWidth: 110,
    baseUrlMinWidth: 220,
    runtimeConfigMinWidth: 220,
    statusWidth: 110,
    actionsWidth: 260,
  },
  models: {
    modelKeyMinWidth: 180,
    displayNameMinWidth: 160,
    upstreamModelMinWidth: 170,
    providerMinWidth: 140,
    healthWidth: 110,
    statusWidth: 110,
    actionsWidth: 290,
  },
  routes: {
    modelKeyMinWidth: 180,
    modelNameMinWidth: 160,
    providerMinWidth: 140,
    priorityWidth: 100,
    statusWidth: 110,
    descriptionMinWidth: 180,
  },
  usage: {
    modelNameMinWidth: 160,
    metricWidth: 120,
    tokenWidth: 150,
    latencyWidth: 130,
    providerMinWidth: 140,
    compactMetricWidth: 90,
    compactRateWidth: 110,
  },
} as const

export const uiFormTokens = {
  providerConfigRows: 5,
  modelParamsRows: 4,
  shortTextareaRows: 2,
} as const
