

#!/bin/bash

#Copiando estructura de directorios
rsync -av --ignore-existing -f"+ */" -f"- *" input/ output/

#Ejecutar SpeciesNet en las imágenes
python3 -m speciesnet.scripts.run_model --country GT --folders "input/" --predictions_json "output/"



