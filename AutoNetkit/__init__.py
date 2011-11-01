import AutoNetkit.algorithms
from AutoNetkit.algorithms import *

import AutoNetkit.compiler
from AutoNetkit.compiler import *

import AutoNetkit.examples
from AutoNetkit.examples import *

import AutoNetkit.deploy
from AutoNetkit.deploy import *

import AutoNetkit.internal
from AutoNetkit.internal import *

import AutoNetkit.plotting
from AutoNetkit.plotting import *

import AutoNetkit.readwrite
from AutoNetkit.readwrite import *

# Internet goes last, as it imports compiler
# Loading first would mean compiler loaded before the other modules
import internet
