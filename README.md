# Account Payment Approval

Módulos de Odoo para que una factura de proveedor **no se pueda pagar hasta que la apruebe** el
responsable definido en el proveedor.

| | |
|---|---|
| **Módulos** | `account_move_payment_tier_validation` |
| **Licencia** | AGPL-3 |
| **Versiones** | 18.0 — Community y Enterprise |
| **Depende de** | [`base_tier_validation`](https://github.com/OCA/server-ux/tree/18.0/base_tier_validation) (OCA server-ux) |

## Para qué sirve

Odoo trae un bloqueo de pago manual en la factura, pero sin aprobador: cualquier usuario de
contabilidad lo levanta. `account_move_payment_tier_validation` lo convierte en un circuito de
aprobación:

1. En el proveedor se carga el **Aprobador de pagos** (por compañía).
2. Al **confirmar** la factura, se contabiliza normalmente (entra al Libro IVA Compras en su
   fecha contable), se pide la aprobación y el pago queda **Bloqueado**.
3. Cuando el aprobador aprueba, el pago se desbloquea solo. Si rechaza, sigue bloqueado.

Mientras está bloqueada, la factura no se puede pagar por ningún camino (botón *Pagar*, pago
desde la lista, conciliación bancaria o manual); sí se puede compensar con una nota de crédito.
El aprobador ve sus pendientes en el ícono de aprobaciones de la barra superior y en la lista de
facturas, y puede **aprobar en lote** desde la lista.

El detalle de comportamiento y configuración está en el
[README del módulo](account_move_payment_tier_validation/README.md).

## Instalación

1. Tener en el `addons_path` este repositorio y [OCA/server-ux](https://github.com/OCA/server-ux)
   (rama de la misma versión).
2. Instalar **Facturas de proveedor - Aprobación de pago por niveles**.
3. Cargar el *Aprobador de pagos* en los proveedores.

No usar junto con `account_move_tier_validation` de OCA (bloquea la confirmación en lugar del
pago, y los dos montan la validación sobre `account.move`).

## Ramas

| Rama | Estado |
|---|---|
| `18.0` | Probada (tests del módulo en Odoo 18 Community). |
| `19.0` | Pendiente: el código evita APIs que cambian en 19, pero falta `base_tier_validation` 19.0 en OCA para probarla. |
