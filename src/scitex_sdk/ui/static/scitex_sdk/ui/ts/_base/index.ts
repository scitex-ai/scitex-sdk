/**
 * Base module — shared abstractions for scitex-ui components.
 */
export { BaseComponent } from "./BaseComponent";
export type { BaseComponentConfig } from "./types";
export {
  MOUNT_ATTRIBUTE,
  MOUNT_META_NAME,
  MountPrefixMissingError,
  apiUrl,
  mountPrefix,
} from "./mount";
export {
  APP_SCOPE_META_NAME,
  SCOPE_USER,
  SCOPE_PROJECT,
  AppScopeMarkerInvalidError,
  appScope,
  mayOfferProjectSelector,
} from "./scope";
export type { AppScope } from "./scope";
export {
  I18N_LANGUAGES,
  SHELL_STRINGS,
  shellTranslate,
} from "./i18n";
export type { I18NLanguage, ShellStringKey } from "./i18n";
export {
  JS_CATALOG_ELEMENT_PREFIX,
  evaluatePluralExpression,
  gettext,
  gettext_noop,
  installCatalog,
  interpolate,
  loadCatalogsFromDocument,
  ngettext,
  npgettext,
  pgettext,
  pluralidx,
  resetCatalog,
} from "./gettext";
export type { CatalogEntry, JsCatalogPayload } from "./gettext";
