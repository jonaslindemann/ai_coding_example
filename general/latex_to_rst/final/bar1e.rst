bar1e
^^^^^

:purpose: Compute element stiffness matrix for a one dimensional bar element.

.. figure:: bar1e_1.eps
   :align: center

:description:

``bar1e`` provides the element stiffness matrix ``Ke`` for a
one dimensional bar element.
The input variables

.. math::

   \begin{array}{l}
   \text{ex} = [\;x_1 \;\; x_2 \;]  
   \end{array}
   \quad\quad
   \text{ep} = \left[\;E \;A\;\right]

supply the element nodal coordinates
:math:`x_1` and :math:`x_2`, the modulus of elasticity :math:`E`,
and the cross section area :math:`A`.

The element load vector ``fe`` can also be computed if uniformly
distributed load is applied to the element.
The optional input variable

.. math::

   \text{eq} =\left[\begin{array}{cc} q_{\bar{x}}  \end{array} \right]

then contains the distributed load per unit length, :math:`q_{\bar{x}}`.

.. figure:: bar1e_2.eps
   :align: center

Syntax
------

.. only:: matlab

   .. code-block:: matlab

      Ke = bar1e(ex,ep)
      [Ke,fe] = bar1e(ex,ep,eq)

.. only:: python

   .. code-block:: python

      Ke = bar1e(ex,ep)
      Ke, fe = bar1e(ex,ep,eq)

Theory
------

The element stiffness matrix :math:`\bar{{\bf K}}^e`, stored in ``Ke``, is computed
according to

.. math::

   \bar{\bf K}^e=\frac{D_{EA}}{L}\left[
   \begin{array}{rr} 1 & -1  \\ -1 & 1  \end{array} \right]

where the axial stiffness :math:`D_{EA}` and the length :math:`L` are given by

.. math::

   D_{EA}=EA;\quad L= x_2-x_1 

The element load vector :math:`\bar{\bf f}_l^e`, stored in ``fe``, is computed
according to

.. math::

   \bar{\bf f}_l^e =\frac{q_{\bar{x}}L}{2}
   \left[
   \begin{array}{c}  1 \\  1 \end{array} \right]