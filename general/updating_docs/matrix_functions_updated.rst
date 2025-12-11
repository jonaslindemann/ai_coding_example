Matrix functions
================

.. _Matrix:

.. only:: matlab

    The group of matrix functions comprises functions for vector and matrix operations and also functions for sparse matrix handling. MATLAB has two storage modes, full and sparse. Only nonzero entries and their indices are stored for sparse matrices. Sparse matrices are not created automatically. But once initiated, sparsity propagates. Operations on sparse matrices produce sparse matrices and operations on a mixture of sparse and full matrices also normally produce sparse matrices.

.. only:: python

    The group of matrix functions comprises functions for vector and matrix operations and also functions for sparse matrix handling. In Python, these operations are primarily handled by NumPy arrays and SciPy sparse matrices. NumPy provides dense arrays while SciPy provides sparse matrix functionality. Unlike MATLAB, Python distinguishes between different sparse matrix formats (CSR, CSC, COO, etc.) for different use cases.

    If you want use the functions described in this chapter, you need to import the NumPy and SciPy libraries. It is common practice to import these libraries with the following aliases:

    .. code-block:: python

        import numpy as np
        import scipy.sparse as sp
        import matplotlib.pyplot as plt

The following functions are described in this chapter:

.. only:: matlab

    **Vector and matrix operations**

    +----------------------+--------------------------------------------------+
    | ``[ ] ( )`` =        | Special characters                               |
    +----------------------+--------------------------------------------------+
    | ``' . , ;``          | Special characters                               |
    +----------------------+--------------------------------------------------+
    | ``:``                | Create vectors and do matrix subscripting        |
    +----------------------+--------------------------------------------------+
    | ``+ - * /``          | Matrix arithmetic                                |
    +----------------------+--------------------------------------------------+
    | ``abs``              | Absolute value                                   |
    +----------------------+--------------------------------------------------+
    | ``det``              | Matrix determinant                               |
    +----------------------+--------------------------------------------------+
    | ``diag``             | Diagonal matrices and diagonals of a matrix      |
    +----------------------+--------------------------------------------------+
    | ``inv``              | Matrix inverse                                   |
    +----------------------+--------------------------------------------------+
    | ``length``           | Vector length                                    |
    +----------------------+--------------------------------------------------+
    | ``max``              | Maximum element(s) of a matrix                   |
    +----------------------+--------------------------------------------------+
    | ``min``              | Minimum element(s) of a matrix                   |
    +----------------------+--------------------------------------------------+
    | ``ones``             | Generate a matrix of all ones                    |
    +----------------------+--------------------------------------------------+
    | ``size``             | Matrix dimensions                                |
    +----------------------+--------------------------------------------------+
    | ``sqrt``             | Square root                                      |
    +----------------------+--------------------------------------------------+
    | ``sum``              | Sum of the elements of a matrix                  |
    +----------------------+--------------------------------------------------+
    | ``zeros``            | Generate a zero matrix                           |
    +----------------------+--------------------------------------------------+

    **Sparse matrix handling**

    +----------------------+--------------------------------------------------+
    | ``full``             | Convert sparse matrix to full matrix             |
    +----------------------+--------------------------------------------------+
    | ``sparse``           | Create sparse matrix                             |
    +----------------------+--------------------------------------------------+
    | ``spy``              | Visualize sparsity structure                     |
    +----------------------+--------------------------------------------------+

.. only:: python

    **Vector and matrix operations**

    +----------------------+--------------------------------------------------+
    | ``[ ] ( )`` =        | Special characters                               |
    +----------------------+--------------------------------------------------+
    | ``' , ;``            | Special characters                               |
    +----------------------+--------------------------------------------------+
    | ``:``                | Create arrays and do array indexing              |
    +----------------------+--------------------------------------------------+
    | ``+ - * /``          | Array arithmetic                                 |
    +----------------------+--------------------------------------------------+
    | ``np.abs``           | Absolute value                                   |
    +----------------------+--------------------------------------------------+
    | ``np.linalg.det``    | Matrix determinant                               |
    +----------------------+--------------------------------------------------+
    | ``np.diag``          | Diagonal arrays and diagonals of an array        |
    +----------------------+--------------------------------------------------+
    | ``np.linalg.inv``    | Matrix inverse                                   |
    +----------------------+--------------------------------------------------+
    | ``len``              | Array length                                     |
    +----------------------+--------------------------------------------------+
    | ``np.max``           | Maximum element(s) of an array                   |
    +----------------------+--------------------------------------------------+
    | ``np.min``           | Minimum element(s) of an array                   |
    +----------------------+--------------------------------------------------+
    | ``np.ones``          | Generate an array of all ones                    |
    +----------------------+--------------------------------------------------+
    | ``np.shape``         | Array dimensions                                 |
    +----------------------+--------------------------------------------------+
    | ``np.sqrt``          | Square root                                      |
    +----------------------+--------------------------------------------------+
    | ``np.sum``           | Sum of the elements of an array                  |
    +----------------------+--------------------------------------------------+
    | ``np.zeros``         | Generate a zero array                            |
    +----------------------+--------------------------------------------------+

    **Sparse matrix handling**

    +---------------------------+--------------------------------------------------+
    | ``sparse_matrix.toarray`` | Convert sparse matrix to dense array            |
    +---------------------------+--------------------------------------------------+
    | ``scipy.sparse``          | Create sparse matrix                             |
    +---------------------------+--------------------------------------------------+
    | ``plt.spy``               | Visualize sparsity structure                     |
    +---------------------------+--------------------------------------------------+

.. only:: matlab

    Special characters [ ] ( ) = ' . , ;
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    .. index:: [ ] ( ) = ' . , ;

    :Purpose:

        Special characters.

    :Syntax:

    .. code-block:: matlab

        [ ] ( ) = ' . , ;

    :Description:

        **[ ]** 
            Brackets are used to form vectors and matrices.
        
        **( )** 
            Parentheses are used to indicate precedence in arithmetic expressions and to specify an element of a matrix.
        
        **=** 
            Used in assignment statements.
        
        **'** 
            Matrix transpose. ``X'`` is the transpose of ``X``. If ``X`` is complex, the apostrophe sign performs complex conjugate as well. Do ``X.'`` if only the transpose of the complex matrix is desired.
        
        **.**
            Decimal point. 314/100, 3.14 and 0.314e1 are all the same.
        
        **,**
            Comma. Used to separate matrix subscripts and function arguments.
        
        **;**
            Semicolon. Used inside brackets to end rows. Used after an expression to suppress printing or to separate statements.

    :Examples:

        By the statement:

        .. code-block:: matlab

            a = 2

        the scalar ``a`` is assigned a value of 2. An element in a matrix may be assigned a value according to:

        .. code-block:: matlab

            A(2,5) = 3

        The statement:

        .. code-block:: matlab

            D = [ 1  2 ; 3  4 ]

        results in matrix:

        .. math::

            \mathbf{D} = \begin{bmatrix}
            1 & 2 \\
            3 & 4
            \end{bmatrix}

        stored in the matrix bank. To copy the contents of the matrix ``D`` to a matrix ``E``, use:

        .. code-block:: matlab

            E = D

        The character ' is used in the following statement to store the transpose of the matrix ``A`` in a new matrix ``F``:

        .. code-block:: matlab

            F = A'

    :Note:

        These are MATLAB built-in characters.

.. only:: python

    Special characters [ ] ( ) = ' , ;
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    .. index:: [ ] ( ) = ' , ;

    :Purpose:

        Special characters for array operations.

    :Syntax:

    .. code-block:: python

        [ ] ( ) = ' , ;

    :Description:

        **[ ]** 
            Brackets are used to create lists and arrays, and for indexing.
        
        **( )** 
            Parentheses are used to indicate precedence in arithmetic expressions, for function calls, and to create tuples.
        
        **=** 
            Used in assignment statements.
        
        **'** 
            String delimiter. For matrix transpose, use ``.T`` or ``np.transpose()``.
        
        **,**
            Comma. Used to separate array indices and function arguments.
        
        **;**
            Semicolon. Used to separate statements on the same line (not commonly used in Python).

    :Examples:

        By the statement:

        .. code-block:: python

            a = 2

        the scalar ``a`` is assigned a value of 2. An element in an array may be assigned a value according to:

        .. code-block:: python

            A[1, 4] = 3  # Note: Python uses 0-based indexing

        The statement:

        .. code-block:: python

            D = np.array([[1, 2], [3, 4]])

        results in array:

        .. math::

            \mathbf{D} = \begin{bmatrix}
            1 & 2 \\
            3 & 4
            \end{bmatrix}

        stored in memory. To copy the contents of the array ``D`` to an array ``E``, use:

        .. code-block:: python

            E = D.copy()  # or E = np.copy(D)

        The transpose of array ``A`` is stored in a new array ``F`` using:

        .. code-block:: python

            F = A.T  # or F = np.transpose(A)

    :Note:

        These are Python built-in syntax elements. NumPy must be imported as ``import numpy as np``.
.. only:: matlab

    : (colon operator)
    ^^^^^^^^^^^^^^^^^^

    .. index:: :

    :Purpose:

        Create vectors and do matrix subscripting.

    :Description:

        The colon operator uses the following rules to create regularly spaced vectors:

        **j : k** 
            is the same as [ ``j``, ``j + 1, ... , k`` ]
        
        **j : i : k** 
            is the same as [ ``j``, ``j + i, j + 2i, ... , k`` ]

        The colon notation may also be used to pick out selected rows, columns, and elements of vectors and matrices:

        **A( : , j )** 
            is the ``j`` :th column of ``A``
        
        **A( i , : )** 
            is the ``i`` :th row of ``A``

    :Examples:

        The colon ':' used with integers:

        .. code-block:: matlab

            d = 1:4

        results in a row vector:

        .. math::

            \mathbf{d} = \begin{bmatrix} 1 & 2 & 3 & 4 \end{bmatrix}

        stored in the workspace.

        The colon notation may be used to display selected rows and columns of a matrix on the terminal. For example, if we have created a 3-times-4 matrix ``D`` by the statement:

        .. code-block:: matlab

            D = [ d ; 2*d ; 3*d ]

        resulting in:

        .. math::

            \mathbf{D} = \begin{bmatrix}
            1 & 2 & 3 & 4 \\
            2 & 4 & 6 & 8 \\
            3 & 6 & 9 & 12
            \end{bmatrix}

        columns three and four are displayed by entering:

        .. code-block:: matlab

            D( :, 3:4 )

        resulting in:

        .. math::

            \mathbf{D}( :, 3:4 ) = \begin{bmatrix}
            3 & 4 \\
            6 & 8 \\
            9 & 12
            \end{bmatrix}

        In order to copy parts of the ``D`` matrix into another matrix the colon notation is used as:

        .. code-block:: matlab

            E( 3:4, 2:3 ) = D( 1:2, 3:4 )

        Assuming the matrix ``E`` was a zero matrix before the statement is executed, the result will be:

        .. math::

            \mathbf{E} = \begin{bmatrix}
            0 & 0 & 0 & 0 \\
            0 & 0 & 0 & 0 \\
            0 & 3 & 4 & 0 \\
            0 & 6 & 8 & 0
            \end{bmatrix}

    :Note:

        This is a MATLAB built-in character.

.. only:: python

    : (slice operator) and np.arange
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    .. index:: :, np.arange

    :Purpose:

        Create arrays and do array indexing/slicing.

    :Description:

        In Python with NumPy, array creation and slicing use different syntax:

        **np.arange(j, k)** 
            creates array [ ``j``, ``j + 1, ... , k-1`` ] (note: k is excluded)
        
        **np.arange(j, k, i)** 
            creates array [ ``j``, ``j + i, j + 2i, ... `` ] up to but not including ``k``

        The colon notation is used for array slicing:

        **A[ : , j ]** 
            is the ``j`` :th column of ``A``
        
        **A[ i , : ]** 
            is the ``i`` :th row of ``A``

    :Examples:

        To create a sequence similar to MATLAB's ``1:4``:

        .. code-block:: python

            d = np.arange(1, 5)  # Creates [1, 2, 3, 4]

        results in a 1D array:

        .. math::

            \mathbf{d} = \begin{bmatrix} 1 & 2 & 3 & 4 \end{bmatrix}

        stored in memory.

        Array slicing is used to access selected rows and columns. For example, if we have created a 3×4 array ``D``:

        .. code-block:: python

            D = np.array([d, 2*d, 3*d])

        resulting in:

        .. math::

            \mathbf{D} = \begin{bmatrix}
            1 & 2 & 3 & 4 \\
            2 & 4 & 6 & 8 \\
            3 & 6 & 9 & 12
            \end{bmatrix}

        columns two and three (indices 2:4) are accessed by:

        .. code-block:: python

            D[:, 2:4]  # Note: 0-based indexing, end index excluded

        resulting in:

        .. math::

            \mathbf{D}[:, 2:4] = \begin{bmatrix}
            3 & 4 \\
            6 & 8 \\
            9 & 12
            \end{bmatrix}

        To copy parts of array ``D`` into another array, use slicing:

        .. code-block:: python

            E[2:4, 1:3] = D[0:2, 2:4]  # 0-based indexing

        Assuming array ``E`` was a zero array before the statement, the result will be:

        .. math::

            \mathbf{E} = \begin{bmatrix}
            0 & 0 & 0 & 0 \\
            0 & 0 & 0 & 0 \\
            0 & 3 & 4 & 0 \\
            0 & 6 & 8 & 0
            \end{bmatrix}

    :Note:

        These are Python/NumPy built-in operations. Note the 0-based indexing and exclusive end indices.
.. only:: matlab

    + - * / (arithmetic operators)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    .. index:: + - * /

    :Purpose:

        Matrix arithmetic.

    :Syntax:

    .. code-block:: matlab

        A + B
        A - B
        A * B
        A/s

    :Description:

        Matrix operations are defined by the rules of linear algebra.

    :Examples:

        An example of a sequence of matrix-to-matrix operations is:

        .. code-block:: matlab

            D = A + B - C

        A matrix-to-vector multiplication followed by a vector-to-vector subtraction may be defined by the statement:

        .. code-block:: matlab

            b = c - A * x

        and finally, to scale a matrix by a scalar ``s`` we may use:

        .. code-block:: matlab

            B = A/s

    :Note:

        These are MATLAB built-in operators.

.. only:: python

    + - * / @ (arithmetic operators)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    .. index:: + - * / @

    :Purpose:

        Array arithmetic operations.

    :Syntax:

    .. code-block:: python

        A + B
        A - B
        A * B    # element-wise multiplication
        A @ B    # matrix multiplication
        A / s    # element-wise division
        A // s   # floor division

    :Description:

        NumPy array operations can be element-wise or matrix operations. Use ``@`` for matrix multiplication and ``*`` for element-wise multiplication.

    :Examples:

        An example of a sequence of array-to-array operations is:

        .. code-block:: python

            D = A + B - C

        A matrix-to-vector multiplication followed by a vector-to-vector subtraction may be defined by the statement:

        .. code-block:: python

            b = c - A @ x  # Use @ for matrix multiplication

        and finally, to scale an array by a scalar ``s`` we may use:

        .. code-block:: python

            B = A / s

    :Note:

        These are NumPy array operations. For matrix multiplication, use ``@`` or ``np.dot()``.
.. only:: matlab

    abs
    ^^^

    .. index:: abs

    :Purpose:

        Absolute value.

    :Syntax:

    .. code-block:: matlab

        B = abs(A)

    :Description:

        ``B = abs(A)`` computes the absolute values of the elements of matrix ``A`` and stores them in matrix ``B``.

    :Examples:

        Assume the matrix:

        .. math::

            \mathbf{C} = \begin{bmatrix}
            -7 & 4 \\
            -3 & -8
            \end{bmatrix}

        The statement:

        .. code-block:: matlab

            D = abs(C)

        results in a matrix:

        .. math::

            \mathbf{D} = \begin{bmatrix}
            7 & 4 \\
            3 & 8
            \end{bmatrix}

        stored in the workspace.

    :Note:

        This is a MATLAB built-in function. For more information about the ``abs`` function, type ``help abs``.

.. only:: python

    np.abs
    ^^^^^^

    .. index:: np.abs

    :Purpose:

        Absolute value.

    :Syntax:

    .. code-block:: python

        B = np.abs(A)

    :Description:

        ``B = np.abs(A)`` computes the absolute values of the elements of array ``A`` and stores them in array ``B``.

    :Examples:

        Assume the array:

        .. math::

            \mathbf{C} = \begin{bmatrix}
            -7 & 4 \\
            -3 & -8
            \end{bmatrix}

        The statement:

        .. code-block:: python

            D = np.abs(C)

        results in an array:

        .. math::

            \mathbf{D} = \begin{bmatrix}
            7 & 4 \\
            3 & 8
            \end{bmatrix}

        stored in memory.

    :Note:

        This is a NumPy function. Alternative: ``np.absolute()``. For more information, see NumPy documentation.
.. only:: matlab

    det
    ^^^

    .. index:: det

    :Purpose:

        Matrix determinant.

    :Syntax:

    .. code-block:: matlab

        a = det(A)

    :Description:

        ``a = det(A)`` computes the determinant of the matrix ``A`` and stores it in the scalar ``a``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``det`` function, type ``help det``.

.. only:: python

    np.linalg.det
    ^^^^^^^^^^^^^

    .. index:: np.linalg.det

    :Purpose:

        Matrix determinant.

    :Syntax:

    .. code-block:: python

        a = np.linalg.det(A)

    :Description:

        ``a = np.linalg.det(A)`` computes the determinant of the square array ``A`` and stores it in the scalar ``a``.

    :Note:

        This is a NumPy linear algebra function. For more information, see NumPy documentation.
.. only:: matlab

    diag
    ^^^^

    .. index:: diag

    :Purpose:

        Diagonal matrices and diagonals of a matrix.

    :Syntax:

    .. code-block:: matlab

        M = diag(v)
        v = diag(M)

    :Description:

        For a vector ``v`` with *n* components, the statement ``M = diag(v)`` results in an *n* × *n* matrix ``M`` with the elements of ``v`` as the main diagonal.

        For a *n* × *n* matrix ``M``, the statement ``v = diag(M)`` results in a column vector ``v`` with *n* components formed by the main diagonal in ``M``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``diag`` function, type ``help diag``.

.. only:: python

    np.diag
    ^^^^^^^

    .. index:: np.diag

    :Purpose:

        Diagonal arrays and diagonals of an array.

    :Syntax:

    .. code-block:: python

        M = np.diag(v)
        v = np.diag(M)

    :Description:

        For a 1D array ``v`` with *n* elements, the statement ``M = np.diag(v)`` results in an *n* × *n* array ``M`` with the elements of ``v`` as the main diagonal.

        For a 2D array ``M``, the statement ``v = np.diag(M)`` results in a 1D array ``v`` formed by the main diagonal of ``M``.

    :Note:

        This is a NumPy function. Use ``np.diagflat()`` for a more general version that works with multi-dimensional input.
.. only:: matlab

    full
    ^^^^

    .. index:: full

    :Purpose:

        Convert sparse matrices to full storage class.

    :Syntax:

    .. code-block:: matlab

        A = full(S)

    :Description:

        ``A = full(S)`` converts the storage of a matrix from sparse to full. If ``A`` is already full, ``full(A)`` returns ``A``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``full`` function, type ``help full``.

.. only:: python

    .toarray() / .todense()
    ^^^^^^^^^^^^^^^^^^^^^^^

    .. index:: .toarray, .todense

    :Purpose:

        Convert sparse matrices to dense arrays.

    :Syntax:

    .. code-block:: python

        A = S.toarray()    # Convert to NumPy array
        A = S.todense()    # Convert to matrix (deprecated)

    :Description:

        ``A = S.toarray()`` converts a sparse matrix ``S`` to a dense NumPy array ``A``.

        ``A = S.todense()`` converts to a matrix object (deprecated, use ``toarray()``).

    :Note:

        These are methods of scipy.sparse matrices. Use ``toarray()`` for better compatibility with NumPy operations.
.. only:: matlab

    inv
    ^^^

    .. index:: inv

    :Purpose:

        Matrix inverse.

    :Syntax:

    .. code-block:: matlab

        B = inv(A)

    :Description:

        ``B = inv(A)`` computes the inverse of the square matrix ``A`` and stores the result in the matrix ``B``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``inv`` function, type ``help inv``.

.. only:: python

    np.linalg.inv
    ^^^^^^^^^^^^^

    .. index:: np.linalg.inv

    :Purpose:

        Matrix inverse.

    :Syntax:

    .. code-block:: python

        B = np.linalg.inv(A)

    :Description:

        ``B = np.linalg.inv(A)`` computes the inverse of the square array ``A`` and stores the result in the array ``B``.

    :Note:

        This is a NumPy linear algebra function. For better numerical stability, consider using ``np.linalg.pinv()`` for pseudo-inverse or ``scipy.linalg.solve()`` for solving linear systems.
.. only:: matlab

    length
    ^^^^^^

    .. index:: length

    :Purpose:

        Vector length.

    :Syntax:

    .. code-block:: matlab

        n = length(x)

    :Description:

        ``n = length(x)`` returns the dimension of the vector ``x``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``length`` function, type ``help length``.

.. only:: python

    len / np.size
    ^^^^^^^^^^^^^

    .. index:: len, np.size

    :Purpose:

        Array length.

    :Syntax:

    .. code-block:: python

        n = len(x)        # For 1D arrays
        n = np.size(x)    # Total number of elements
        n = x.size        # Total number of elements

    :Description:

        ``n = len(x)`` returns the length of the first dimension of array ``x``.
        
        ``n = np.size(x)`` returns the total number of elements in array ``x``.

    :Note:

        ``len()`` is a Python built-in function. ``np.size()`` is a NumPy function that's more similar to MATLAB's ``length()``.
.. only:: matlab

    max
    ^^^

    .. index:: max

    :Purpose:

        Maximum element(s) of a matrix.

    :Syntax:

    .. code-block:: matlab

        b = max(A)

    :Description:

        For a vector ``a``, the statement ``b = max(a)`` assigns the scalar ``b`` the maximum element of the vector ``a``.

        For a matrix ``A``, the statement ``b = max(A)`` returns a row vector ``b`` containing the maximum elements found in each column vector in ``A``.

        The maximum element found in a matrix may thus be determined by ``c = max(max(A))``.

    :Examples:

        Assume the matrix ``B`` is defined as:

        .. math::

            \mathbf{B} = \begin{bmatrix}
            -7 & 4 \\
            -3 & -8
            \end{bmatrix}

        The statement:

        .. code-block:: matlab

            d = max(B)

        results in a row vector:

        .. math::

            \mathbf{d} = \begin{bmatrix} -3 & 4 \end{bmatrix}

        The maximum element in the matrix ``B`` may be found by ``e = max(d)`` which results in the scalar ``e = 4``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``max`` function, type ``help max``.

.. only:: python

    np.max
    ^^^^^^

    .. index:: np.max

    :Purpose:

        Maximum element(s) of an array.

    :Syntax:

    .. code-block:: python

        b = np.max(A)           # Maximum of entire array
        b = np.max(A, axis=0)   # Maximum along columns
        b = np.max(A, axis=1)   # Maximum along rows

    :Description:

        For a 1D array ``a``, ``b = np.max(a)`` returns the maximum element.

        For a 2D array ``A``, ``b = np.max(A, axis=0)`` returns an array containing the maximum elements found in each column.

        The maximum element in an array may be found by ``c = np.max(A)``.

    :Examples:

        Assume the array ``B`` is defined as:

        .. math::

            \mathbf{B} = \begin{bmatrix}
            -7 & 4 \\
            -3 & -8
            \end{bmatrix}

        The statement:

        .. code-block:: python

            d = np.max(B, axis=0)

        results in an array:

        .. math::

            \mathbf{d} = \begin{bmatrix} -3 & 4 \end{bmatrix}

        The maximum element in array ``B`` may be found by ``e = np.max(B)`` which results in the scalar ``e = 4``.

    :Note:

        This is a NumPy function. Alternative: ``np.amax()`` or ``A.max()``.
.. only:: matlab

    min
    ^^^

    .. index:: min

    :Purpose:

        Minimum element(s) of a matrix.

    :Syntax:

    .. code-block:: matlab

        b = min(A)

    :Description:

        For a vector ``a``, the statement ``b = min(a)`` assigns the scalar ``b`` the minimum element of the vector ``a``.

        For a matrix ``A``, the statement ``b = min(A)`` returns a row vector ``b`` containing the minimum elements found in each column vector in ``A``.

        The minimum element found in a matrix may thus be determined by ``c = min(min(A))``.

    :Examples:

        Assume the matrix ``B`` is defined as:

        .. math::

            \mathbf{B} = \begin{bmatrix}
            -7 & 4 \\
            -3 & -8
            \end{bmatrix}

        The statement:

        .. code-block:: matlab

            d = min(B)

        results in a row vector:

        .. math::

            \mathbf{d} = \begin{bmatrix} -7 & -8 \end{bmatrix}

        The minimum element in the matrix ``B`` is then found by ``e = min(d)``, which results in the scalar ``e = -8``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``min`` function, type ``help min``.

.. only:: python

    np.min
    ^^^^^^

    .. index:: np.min

    :Purpose:

        Minimum element(s) of an array.

    :Syntax:

    .. code-block:: python

        b = np.min(A)           # Minimum of entire array
        b = np.min(A, axis=0)   # Minimum along columns
        b = np.min(A, axis=1)   # Minimum along rows

    :Description:

        For a 1D array ``a``, ``b = np.min(a)`` returns the minimum element.

        For a 2D array ``A``, ``b = np.min(A, axis=0)`` returns an array containing the minimum elements found in each column.

        The minimum element in an array may be found by ``c = np.min(A)``.

    :Examples:

        Assume the array ``B`` is defined as:

        .. math::

            \mathbf{B} = \begin{bmatrix}
            -7 & 4 \\
            -3 & -8
            \end{bmatrix}

        The statement:

        .. code-block:: python

            d = np.min(B, axis=0)

        results in an array:

        .. math::

            \mathbf{d} = \begin{bmatrix} -7 & -8 \end{bmatrix}

        The minimum element in array ``B`` is found by ``e = np.min(B)``, which results in the scalar ``e = -8``.

    :Note:

        This is a NumPy function. Alternative: ``np.amin()`` or ``A.min()``.
.. only:: matlab

    ones
    ^^^^

    .. index:: ones

    :Purpose:

        Generate a matrix of all ones.

    :Syntax:

    .. code-block:: matlab

        A = ones(m,n)

    :Description:

        ``A = ones(m,n)`` results in an ``m``-times-``n`` matrix ``A`` with all ones.

    :Note:

        This is a MATLAB built-in function. For more information about the ``ones`` function, type ``help ones``.

.. only:: python

    np.ones
    ^^^^^^^

    .. index:: np.ones

    :Purpose:

        Generate an array of all ones.

    :Syntax:

    .. code-block:: python

        A = np.ones((m, n))
        A = np.ones(shape)

    :Description:

        ``A = np.ones((m, n))`` results in an ``m``×``n`` array ``A`` with all ones.
        
        ``A = np.ones(shape)`` creates an array with the specified shape filled with ones.

    :Note:

        This is a NumPy function. Note the tuple syntax for shape ``(m, n)``.

.. only:: matlab

    size
    ^^^^

    .. index:: size

    :Purpose:

        Matrix dimensions.

    :Syntax:

    .. code-block:: matlab

        d = size(A)
        [m,n] = size(A)

    :Description:

        ``d = size(A)`` returns a vector with two integer components, ``d = [m,n]``, from the matrix ``A`` with dimensions ``m`` times ``n``.

        ``[m,n] = size(A)`` returns the dimensions ``m`` and ``n`` of the *m* × *n* matrix ``A``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``size`` function, type ``help size``.

.. only:: python

    np.shape / .shape
    ^^^^^^^^^^^^^^^^^

    .. index:: np.shape, .shape

    :Purpose:

        Array dimensions.

    :Syntax:

    .. code-block:: python

        d = np.shape(A)
        d = A.shape
        m, n = A.shape

    :Description:

        ``d = np.shape(A)`` or ``d = A.shape`` returns a tuple with the dimensions of array ``A``.

        ``m, n = A.shape`` unpacks the dimensions ``m`` and ``n`` of the 2D array ``A``.

    :Note:

        ``.shape`` is an array attribute. ``np.shape()`` is the function equivalent.
.. only:: matlab

    sparse
    ^^^^^^

    .. index:: sparse

    :Purpose:

        Create sparse matrices.

    :Syntax:

    .. code-block:: matlab

        S = sparse(A)
        S = sparse(m,n)

    :Description:

        ``S = sparse(A)`` converts a full matrix to sparse form by extracting all nonzero matrix elements. If ``S`` is already sparse, ``sparse(S)`` returns ``S``.

        ``S = sparse(m,n)`` generates an m-times-n sparse zero matrix.

    :Note:

        This is a MATLAB built-in function. For more information about the ``sparse`` function, type ``help sparse``.

.. only:: python

    scipy.sparse
    ^^^^^^^^^^^^

    .. index:: scipy.sparse

    :Purpose:

        Create sparse matrices.

    :Syntax:

    .. code-block:: python

        import scipy.sparse as sp
        S = sp.csr_matrix(A)        # Convert dense to sparse (CSR format)
        S = sp.coo_matrix(A)        # Convert to COO format
        S = sp.csr_matrix((m, n))   # Create sparse zero matrix

    :Description:

        ``S = sp.csr_matrix(A)`` converts a dense array to sparse CSR (Compressed Sparse Row) format.

        ``S = sp.csr_matrix((m, n))`` creates an m×n sparse zero matrix in CSR format.

        Other formats available: ``csc_matrix`` (CSC), ``coo_matrix`` (COO), ``lil_matrix`` (LIL), etc.

    :Note:

        This requires SciPy. Different sparse formats are optimized for different operations (CSR for row operations, CSC for column operations, etc.).
.. only:: matlab

    spy
    ^^^

    .. index:: spy

    :Purpose:

        Visualize matrix sparsity structure.

    :Syntax:

    .. code-block:: matlab

        spy(S)

    :Description:

        ``spy(S)`` plots the sparsity structure of any matrix ``S``. ``S`` is usually a sparse matrix, but the function also accepts full matrices and the nonzero matrix elements are plotted.

    :Note:

        This is a MATLAB built-in function. For more information about the ``spy`` function, type ``help spy``.

.. only:: python

    plt.spy
    ^^^^^^^

    .. index:: plt.spy

    :Purpose:

        Visualize matrix sparsity structure.

    :Syntax:

    .. code-block:: python

        import matplotlib.pyplot as plt
        plt.spy(S)
        plt.show()

    :Description:

        ``plt.spy(S)`` plots the sparsity pattern of array or sparse matrix ``S``. Nonzero elements are displayed as markers.

        Additional parameters like ``markersize``, ``marker``, etc., can be used to customize the plot.

    :Note:

        This is a matplotlib function. Works with both dense and sparse arrays. For sparse matrices, it's more efficient than converting to dense first.
.. only:: matlab

    sqrt
    ^^^^

    .. index:: sqrt

    :Purpose:

        Square root.

    :Syntax:

    .. code-block:: matlab

        B = sqrt(A)

    :Description:

        ``B = sqrt(A)`` computes the square root of the elements in matrix ``A`` and stores the result in matrix ``B``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``sqrt`` function, type ``help sqrt``.

.. only:: python

    np.sqrt
    ^^^^^^^

    .. index:: np.sqrt

    :Purpose:

        Square root.

    :Syntax:

    .. code-block:: python

        B = np.sqrt(A)

    :Description:

        ``B = np.sqrt(A)`` computes the element-wise square root of array ``A`` and stores the result in array ``B``.

    :Note:

        This is a NumPy function. For complex inputs, it computes the principal square root.
.. only:: matlab

    sum
    ^^^

    .. index:: sum

    :Purpose:

        Sum of the elements of a matrix.

    :Syntax:

    .. code-block:: matlab

        b = sum(A)

    :Description:

        For a vector ``a``, the statement ``b = sum(a)`` results in a scalar ``a`` containing the sum of all elements of ``a``.

        For a matrix ``A``, the statement ``b = sum(A)`` returns a row vector ``b`` containing the sum of the elements found in each column vector of ``A``.

        The sum of all elements of a matrix is determined by ``c = sum(sum(A))``.

    :Note:

        This is a MATLAB built-in function. For more information about the ``sum`` function, type ``help sum``.

.. only:: python

    np.sum
    ^^^^^^

    .. index:: np.sum

    :Purpose:

        Sum of the elements of an array.

    :Syntax:

    .. code-block:: python

        b = np.sum(A)           # Sum of all elements
        b = np.sum(A, axis=0)   # Sum along columns
        b = np.sum(A, axis=1)   # Sum along rows

    :Description:

        For a 1D array ``a``, ``b = np.sum(a)`` returns the sum of all elements.

        For a 2D array ``A``, ``b = np.sum(A, axis=0)`` returns an array containing the sum of elements in each column.

        The sum of all elements in an array is determined by ``c = np.sum(A)``.

    :Note:

        This is a NumPy function. Alternative: ``A.sum()`` method.

.. only:: matlab

    zeros
    ^^^^^

    .. index:: zeros

    :Purpose:

        Generate a zero matrix.

    :Syntax:

    .. code-block:: matlab

        A = zeros(m,n)

    :Description:

        ``A = zeros(m,n)`` results in an ``m``-times-``n`` matrix ``A`` of zeros.

    :Note:

        This is a MATLAB built-in function. For more information about the ``zeros`` function, type ``help zeros``.

.. only:: python

    np.zeros
    ^^^^^^^^

    .. index:: np.zeros

    :Purpose:

        Generate a zero array.

    :Syntax:

    .. code-block:: python

        A = np.zeros((m, n))
        A = np.zeros(shape)

    :Description:

        ``A = np.zeros((m, n))`` results in an ``m``×``n`` array ``A`` of zeros.
        
        ``A = np.zeros(shape)`` creates an array with the specified shape filled with zeros.

    :Note:

        This is a NumPy function. Note the tuple syntax for shape ``(m, n)``.