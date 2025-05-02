import os

from OMPython import ModelicaSystem


class ModelicaSystemFast(ModelicaSystem):
    def getSolutions(self, varList=None, resultfile=None):  # 12
        """
        This method returns tuple of numpy arrays. It can be called:
            •with a list of quantities name in string format as argument: it returns the simulation results of the corresponding names in the same order. Here it supports Python unpacking depending upon the number of variables assigned.
        usage:
        >>> getSolutions()
        >>> getSolutions("Name1")
        >>> getSolutions(["Name1","Name2"])
        >>> getSolutions(resultfile="c:/a.mat")
        >>> getSolutions("Name1",resultfile=""c:/a.mat"")
        >>> getSolutions(["Name1","Name2"],resultfile=""c:/a.mat"")
        """
        if resultfile == None:
            resFile = self.resultfile
        else:
            resFile = resultfile

        # check for result file exits
        if not os.path.exists(resFile):
            errstr = "Error: Result file does not exist {}".format(resFile)
            self._raise_error(errstr=errstr)
            return
            # exit()
        else:
            resultVars = self.getconn.sendExpression("readSimulationResultVars(\"" + resFile + "\")")
            self.getconn.sendExpression("closeSimulationResultFile()")
            if varList is None:
                return resultVars
            elif isinstance(varList, str):
                if varList not in resultVars and varList != "time":
                    errstr = '!!! ' + varList + ' does not exist'
                    self._raise_error(errstr=errstr)
                    return None
                exp = "readSimulationResult(\"" + resFile + '",{' + varList + "})"
                res = self.getconn.sendExpression(exp)

                res = res.replace('{', '[').replace('}', ']')

                res = eval(res)

                exp2 = "closeSimulationResultFile()"
                self.getconn.sendExpression(exp2)
                return res
            elif isinstance(varList, list):
                # varList, = varList
                for v in varList:
                    if v == "time":
                        continue
                    if v not in resultVars:
                        errstr = '!!! ' + v + ' does not exist'
                        self._raise_error(errstr=errstr)
                        return None
                variables = ",".join(varList)
                exp = "readSimulationResult(\"" + resFile + '",{' + variables + "})"
                res = self.getconn.sendExpression(exp, parsed=False)

                res = res.replace('{', '[').replace('}', ']')

                res = eval(res)

                exp2 = "closeSimulationResultFile()"
                self.getconn.sendExpression(exp2)
                return res
            else:
                return None

    def setTempDirectory(self, customBuildDirectory):
        if customBuildDirectory is not None:
            os.makedirs(customBuildDirectory, exist_ok=True)
        super().setTempDirectory(customBuildDirectory)
