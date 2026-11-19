# T-06 — Configurar pruebas automáticas e integración continua

## ST-30. Proteger la rama principal

**Estado:** Completada  
**Responsable:** Bryan Gael Esquivel Pérez (l22420415)

### 1. Descripción

Las ramas `development` y `main` quedaron protegidas con un *ruleset* de GitHub: ya no se puede subir código directo a ellas y todo cambio entra por Pull Request, que solo se puede fusionar cuando el check **`pruebas`** del workflow **CI** (ST-29) termina en verde.

La configuración en GitHub la hizo el profesor, como dueño del repositorio. Esta subtarea documenta cómo quedó, cómo comprobar que funciona y qué hacer en una emergencia.

### 2. Configuración del ruleset

| Opción | Valor |
|---|---|
| Nombre | `proteccion-ramas` |
| Tipo | Branch ruleset |
| Enforcement status | **Active** |
| Bypass list | Repository admin |
| Target branches | `development` y `main` |
| Restrict deletions | Activado |
| Block force pushes | Activado |
| Require a pull request before merging | Activado |
| Required approvals | 1 (se subió de 0 a 1 porque el backlog v3 asigna un revisor a cada subtarea) |
| Require status checks to pass | Activado, con el check **`pruebas`** (job del workflow CI de ST-29) |
| Require branches to be up to date before merging | **Desactivado** |

**¿Por qué no se exige que la rama esté actualizada?** Con esa opción, cada vez que alguien fusiona un PR, todos los demás PR abiertos quedan "desactualizados" y hay que traer `development` otra vez y esperar a que el CI vuelva a correr antes de poder fusionar. Con 17 personas fusionando en el mismo sprint, eso se vuelve una fila interminable de actualizaciones. El CI ya corre sobre el resultado de la fusión (`pull_request` prueba el merge del PR con su rama base), así que el riesgo que queda es bajo.

### 3. Qué significa en la práctica

- **No hay push directo** a `development` ni a `main`: GitHub rechaza el `git push`.
- **Todo entra por Pull Request.** El flujo es: rama `t-XX/st-YY` → push de la rama → PR hacia `development`.
- **Un PR solo se fusiona con `pruebas` en verde.** Si ruff, las migraciones o las pruebas fallan, el botón de merge queda bloqueado.
- **Un PR necesita la aprobación de su revisor** además del check en verde: sin una aprobación (*Approve*) no se puede fusionar.
- Las ramas protegidas **no se pueden borrar** ni reescribir con `git push --force`.
- Los administradores del repositorio están en la *bypass list*: pueden saltarse las reglas, solo para emergencias.

### 4. Cómo se configuró

Solo el **dueño del repositorio** (o alguien con rol *Admin*) puede crear o cambiar rulesets.

1. En GitHub, abrir el repositorio → **Settings**.
2. En el menú lateral: **Rules → Rulesets**.
3. **New ruleset → New branch ruleset**.
4. **Ruleset name:** `proteccion-ramas`.
5. **Enforcement status:** `Active`.
6. **Bypass list → Add bypass:** `Repository admin`.
7. **Target branches → Add target → Include by pattern:** `development`; repetir con `main`.
8. En **Branch rules**, activar:
   - **Restrict deletions**.
   - **Block force pushes**.
   - **Require a pull request before merging**, con **Required approvals** en `1`.
   - **Require status checks to pass** → **Add checks** → escribir `pruebas` y elegirlo (origen: GitHub Actions). Dejar **sin marcar** *Require branches to be up to date before merging*.
9. **Create**.

> El check `pruebas` solo aparece en el buscador de **Add checks** después de que el workflow CI haya corrido al menos una vez en el repositorio.

### 5. Cómo comprobar que funciona

1. **El check es obligatorio:** en cualquier PR hacia `development`, la sección de checks muestra **CI / pruebas** con la etiqueta **Required**.
2. **El merge se bloquea:** mientras `pruebas` está en curso o en rojo, el botón de merge aparece deshabilitado con el aviso de que faltan checks requeridos.
3. **El push directo se rechaza** (probarlo con una cuenta que no sea admin, porque los admins están en la bypass list):

   ```bash
   git fetch origin
   git switch -c prueba-proteccion origin/development
   git commit --allow-empty -m "prueba de protección"
   git push origin HEAD:development    # debe rechazarse con GH013
   # remote: error: GH013: Repository rule violations found for refs/heads/development.
   # ! [remote rejected] HEAD -> development (push declined due to repository rule violations)
   git switch development
   git branch -D prueba-proteccion
   ```

   La prueba se hace en una rama temporal, así que el `development` local no se toca.

**Evidencia observada:** los PR creados antes de ST-29 quedaron en **"Expected — Waiting for status to be reported"** y no se pudieron fusionar hasta que se actualizaron con `development`. Eso confirma que el ruleset exige el check `pruebas`. El workflow sí existía para esos PR: en eventos `pull_request`, GitHub Actions usa el workflow del commit de merge entre la rama del PR y la base, así que basta con que `ci.yml` esté en `development`. El check se quedó en "Expected" porque esos PR no habían tenido ningún evento nuevo (push, reabrir) desde que `ci.yml` llegó a `development`; al actualizarlos se disparó el CI y se reportó el check.

### 6. Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| El PR muestra **pruebas — Expected — Waiting for status to be reported** y nunca avanza | En eventos `pull_request`, GitHub Actions usa el workflow del commit de merge entre la rama del PR y la base, así que `ci.yml` existe aunque la rama sea vieja. El check espera porque el PR no ha tenido ningún evento nuevo (push, reabrir) desde que `ci.yml` llegó a `development`, o porque el PR tiene **conflictos** y GitHub no puede crear el commit de merge | Actualizar la rama con `development` (botón **Update branch** o `git pull origin development` y push) o hacer cualquier push a la rama; si hay conflictos, resolverlos primero. Al subir, el CI corre y reporta el check |
| Una ejecución del CI aparece **cancelada** (círculo gris) | `concurrency` con `cancel-in-progress` (ST-29): un push nuevo a la misma rama cancela la ejecución anterior | No es un error. Cuenta la **última** ejecución; esperar a que termine |
| `pruebas` en rojo | Falló ruff, la revisión de migraciones o pytest | Ver la sección 6 de `docs/T-06/ST-29-workflow-github-actions.md` |
| `git push` rechazado con `GH013` | Se intentó subir directo a `development` o `main` | Crear una rama `t-XX/st-YY`, subirla y abrir un PR |

### 7. Desactivar la protección en una emergencia

Si hace falta saltarse las reglas temporalmente (por ejemplo, GitHub Actions está caído y hay que fusionar una corrección urgente), el dueño del repositorio puede:

1. **Settings → Rules → Rulesets → `proteccion-ramas`**.
2. Cambiar **Enforcement status** a **Disabled** y guardar.
3. Hacer el cambio urgente.
4. **Regresar Enforcement status a Active** en cuanto termine y avisar al equipo.

No se borra el ruleset: desactivarlo conserva toda la configuración para volver a activarla igual.

### 8. Recomendaciones para el profesor

- **Activar Settings → General → Pull Requests → *Always suggest updating pull request branches*.** Así aparece el botón **Update branch** en los PR desactualizados. Usar siempre **Update with merge commit** (no *rebase*), para no reescribir commits que otros ya descargaron.
- **Fusionar siempre con *Create a merge commit*** y pasar `development` a `main` con un PR al final de cada sprint, para que `main` quede como la versión entregada de cada sprint.

### 9. Evidencia

Captura del check `pruebas` marcado como **Required** en un PR:

![Check pruebas requerido en un PR](img/ST-30-check-requerido.png)

### 10. Resultado

`development` y `main` están protegidas: no aceptan push directo, force push ni borrado, y todo cambio entra por Pull Request con el check `pruebas` del CI en verde.

**ST-30 finalizada.**

**Responsable de la actividad:** Bryan Gael Esquivel Pérez (l22420415).
