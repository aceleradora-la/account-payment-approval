# Facturas de proveedor - Aprobación de pago por niveles

Bloquea el **pago** (no la confirmación) de las facturas de proveedor hasta que las apruebe el
aprobador definido en el proveedor. Usa el motor de aprobaciones de OCA
[base_tier_validation](https://github.com/OCA/server-ux/tree/18.0/base_tier_validation), el mismo
de los expedientes.

## Cómo funciona

1. En el proveedor (pestaña *Ventas y compras*, sección *Compra*) se carga el **Aprobador de
   pagos**. Es por compañía.
2. La factura toma ese aprobador (campo **Aprobador del pago**, editable mientras está en borrador).
3. Al **confirmar**, la factura se contabiliza normalmente (entra al Libro IVA Compras en su fecha
   contable), se pide la aprobación y el pago queda **Bloqueado** (el bloqueo nativo de Odoo).
4. Cuando el aprobador aprueba, el pago se desbloquea solo. Si rechaza, sigue bloqueado.

Mientras el pago está bloqueado no se puede pagar por ningún camino: botón *Pagar*, pago desde la
lista, conciliación bancaria o manual. Sí se puede compensar con una nota de crédito.

Detalles:

- Volver la factura a borrador borra la aprobación y el bloqueo; al confirmarla de nuevo se pide
  otra vez.
- Con la aprobación en curso (o ya aprobada) no se pueden cambiar proveedor, cuenta bancaria,
  aprobador, referencia de pago, moneda, plazos ni líneas. Para eso hay que *Reiniciar validación*
  o volver a borrador.
- El desbloqueo manual (botón nativo) no levanta un bloqueo de aprobación pendiente o rechazada.
- Un bloqueo puesto a mano por un usuario también impide pagar (Odoo 18 solo ocultaba el botón).
- Las facturas de proveedores sin aprobador no se bloquean.
- Las facturas confirmadas antes de instalar el módulo no se bloquean; desde la factura se puede
  *Solicitar validación*.

## Dónde se aprueba

- **Contabilidad > Proveedores > Pagos por aprobar**: las facturas que le toca aprobar al usuario
  (filtro *Pendientes de mi aprobación*). Con el filtro *Aprobados por mí* se ve el historial.
- **Ícono de aprobaciones de la barra superior** (de `base_tier_validation`): pendientes del
  usuario por tipo de documento.
- **Contabilidad > Proveedores > Facturas**: mismos filtros, más *Pago en aprobación*, *Pago
  rechazado* y *Pago bloqueado*, y las columnas *Aprobador del pago* y *Aprobación del pago*.
- En instalaciones con Expedientes, también en **Expedientes > Mis aprobaciones > Validaciones**
  (filtro *Facturas de proveedor*), que junta todas las aprobaciones de la fundación.

**Aprobación masiva:** seleccionar facturas (o validaciones) en la lista → *Acciones* →
**Aprobar pago** / **Aprobar pagos de facturas**. Aprueba solo las que le tocan al usuario; las
que exigen comentario se aprueban de a una desde la factura.

El aprobador necesita poder ver facturas (por ejemplo, *Contabilidad: solo lectura*); no necesita
permiso de escritura.

## Configuración

Se instala una regla en *Ajustes > Técnico > Tier Validations > Tier Definition*:
**Aprobación del pago (aprobador del proveedor)**, para facturas y recibos de proveedor con
aprobador. Se puede editar: dominio (por ejemplo, solo arriba de cierto monto), comentario
obligatorio, avisos por correo, o sumar más niveles (otra regla con secuencia distinta, por
ejemplo Tesorería para montos altos).

## Dependencias

- account
- base_tier_validation (OCA server-ux)

No usar junto con `account_move_tier_validation` de OCA: ese módulo bloquea la confirmación y los
dos montan la validación sobre `account.move`.

## Versiones de Odoo

Escrito para 18.0 sin APIs que cambian en 19.0. En Odoo 19 el bloqueo de pago nativo ya se respeta
en el asistente de pagos; el control de conciliación de este módulo lo extiende a los demás
caminos. La migración depende de que exista `base_tier_validation` 19.0 (ver
`MIGRACION_ODOO_19.md`).
