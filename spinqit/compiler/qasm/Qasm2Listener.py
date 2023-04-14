# Copyright 2021 SpinQ Technology Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Generated from Qasm2.g4 by ANTLR 4.9.2
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .Qasm2Parser import Qasm2Parser
else:
    from Qasm2Parser import Qasm2Parser

# This class defines a complete listener for a parse tree produced by Qasm2Parser.
class Qasm2Listener(ParseTreeListener):

    # Enter a parse tree produced by Qasm2Parser#program.
    def enterProgram(self, ctx:Qasm2Parser.ProgramContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#program.
    def exitProgram(self, ctx:Qasm2Parser.ProgramContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#header.
    def enterHeader(self, ctx:Qasm2Parser.HeaderContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#header.
    def exitHeader(self, ctx:Qasm2Parser.HeaderContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#version.
    def enterVersion(self, ctx:Qasm2Parser.VersionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#version.
    def exitVersion(self, ctx:Qasm2Parser.VersionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#include.
    def enterInclude(self, ctx:Qasm2Parser.IncludeContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#include.
    def exitInclude(self, ctx:Qasm2Parser.IncludeContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#globalStatement.
    def enterGlobalStatement(self, ctx:Qasm2Parser.GlobalStatementContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#globalStatement.
    def exitGlobalStatement(self, ctx:Qasm2Parser.GlobalStatementContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#statement.
    def enterStatement(self, ctx:Qasm2Parser.StatementContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#statement.
    def exitStatement(self, ctx:Qasm2Parser.StatementContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumDeclarationStatement.
    def enterQuantumDeclarationStatement(self, ctx:Qasm2Parser.QuantumDeclarationStatementContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumDeclarationStatement.
    def exitQuantumDeclarationStatement(self, ctx:Qasm2Parser.QuantumDeclarationStatementContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#classicalDeclarationStatement.
    def enterClassicalDeclarationStatement(self, ctx:Qasm2Parser.ClassicalDeclarationStatementContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#classicalDeclarationStatement.
    def exitClassicalDeclarationStatement(self, ctx:Qasm2Parser.ClassicalDeclarationStatementContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#assignmentStatement.
    def enterAssignmentStatement(self, ctx:Qasm2Parser.AssignmentStatementContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#assignmentStatement.
    def exitAssignmentStatement(self, ctx:Qasm2Parser.AssignmentStatementContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#returnSignature.
    def enterReturnSignature(self, ctx:Qasm2Parser.ReturnSignatureContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#returnSignature.
    def exitReturnSignature(self, ctx:Qasm2Parser.ReturnSignatureContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#designator.
    def enterDesignator(self, ctx:Qasm2Parser.DesignatorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#designator.
    def exitDesignator(self, ctx:Qasm2Parser.DesignatorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#doubleDesignator.
    def enterDoubleDesignator(self, ctx:Qasm2Parser.DoubleDesignatorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#doubleDesignator.
    def exitDoubleDesignator(self, ctx:Qasm2Parser.DoubleDesignatorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#identifierList.
    def enterIdentifierList(self, ctx:Qasm2Parser.IdentifierListContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#identifierList.
    def exitIdentifierList(self, ctx:Qasm2Parser.IdentifierListContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumDeclaration.
    def enterQuantumDeclaration(self, ctx:Qasm2Parser.QuantumDeclarationContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumDeclaration.
    def exitQuantumDeclaration(self, ctx:Qasm2Parser.QuantumDeclarationContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumArgument.
    def enterQuantumArgument(self, ctx:Qasm2Parser.QuantumArgumentContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumArgument.
    def exitQuantumArgument(self, ctx:Qasm2Parser.QuantumArgumentContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumArgumentList.
    def enterQuantumArgumentList(self, ctx:Qasm2Parser.QuantumArgumentListContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumArgumentList.
    def exitQuantumArgumentList(self, ctx:Qasm2Parser.QuantumArgumentListContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#bitType.
    def enterBitType(self, ctx:Qasm2Parser.BitTypeContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#bitType.
    def exitBitType(self, ctx:Qasm2Parser.BitTypeContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#singleDesignatorType.
    def enterSingleDesignatorType(self, ctx:Qasm2Parser.SingleDesignatorTypeContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#singleDesignatorType.
    def exitSingleDesignatorType(self, ctx:Qasm2Parser.SingleDesignatorTypeContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#doubleDesignatorType.
    def enterDoubleDesignatorType(self, ctx:Qasm2Parser.DoubleDesignatorTypeContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#doubleDesignatorType.
    def exitDoubleDesignatorType(self, ctx:Qasm2Parser.DoubleDesignatorTypeContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#noDesignatorType.
    def enterNoDesignatorType(self, ctx:Qasm2Parser.NoDesignatorTypeContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#noDesignatorType.
    def exitNoDesignatorType(self, ctx:Qasm2Parser.NoDesignatorTypeContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#classicalType.
    def enterClassicalType(self, ctx:Qasm2Parser.ClassicalTypeContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#classicalType.
    def exitClassicalType(self, ctx:Qasm2Parser.ClassicalTypeContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#constantDeclaration.
    def enterConstantDeclaration(self, ctx:Qasm2Parser.ConstantDeclarationContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#constantDeclaration.
    def exitConstantDeclaration(self, ctx:Qasm2Parser.ConstantDeclarationContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#singleDesignatorDeclaration.
    def enterSingleDesignatorDeclaration(self, ctx:Qasm2Parser.SingleDesignatorDeclarationContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#singleDesignatorDeclaration.
    def exitSingleDesignatorDeclaration(self, ctx:Qasm2Parser.SingleDesignatorDeclarationContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#doubleDesignatorDeclaration.
    def enterDoubleDesignatorDeclaration(self, ctx:Qasm2Parser.DoubleDesignatorDeclarationContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#doubleDesignatorDeclaration.
    def exitDoubleDesignatorDeclaration(self, ctx:Qasm2Parser.DoubleDesignatorDeclarationContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#noDesignatorDeclaration.
    def enterNoDesignatorDeclaration(self, ctx:Qasm2Parser.NoDesignatorDeclarationContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#noDesignatorDeclaration.
    def exitNoDesignatorDeclaration(self, ctx:Qasm2Parser.NoDesignatorDeclarationContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#bitDeclaration.
    def enterBitDeclaration(self, ctx:Qasm2Parser.BitDeclarationContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#bitDeclaration.
    def exitBitDeclaration(self, ctx:Qasm2Parser.BitDeclarationContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#classicalDeclaration.
    def enterClassicalDeclaration(self, ctx:Qasm2Parser.ClassicalDeclarationContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#classicalDeclaration.
    def exitClassicalDeclaration(self, ctx:Qasm2Parser.ClassicalDeclarationContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#classicalTypeList.
    def enterClassicalTypeList(self, ctx:Qasm2Parser.ClassicalTypeListContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#classicalTypeList.
    def exitClassicalTypeList(self, ctx:Qasm2Parser.ClassicalTypeListContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#classicalArgument.
    def enterClassicalArgument(self, ctx:Qasm2Parser.ClassicalArgumentContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#classicalArgument.
    def exitClassicalArgument(self, ctx:Qasm2Parser.ClassicalArgumentContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#classicalArgumentList.
    def enterClassicalArgumentList(self, ctx:Qasm2Parser.ClassicalArgumentListContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#classicalArgumentList.
    def exitClassicalArgumentList(self, ctx:Qasm2Parser.ClassicalArgumentListContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#indexIdentifier.
    def enterIndexIdentifier(self, ctx:Qasm2Parser.IndexIdentifierContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#indexIdentifier.
    def exitIndexIdentifier(self, ctx:Qasm2Parser.IndexIdentifierContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#indexIdentifierList.
    def enterIndexIdentifierList(self, ctx:Qasm2Parser.IndexIdentifierListContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#indexIdentifierList.
    def exitIndexIdentifierList(self, ctx:Qasm2Parser.IndexIdentifierListContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#rangeDefinition.
    def enterRangeDefinition(self, ctx:Qasm2Parser.RangeDefinitionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#rangeDefinition.
    def exitRangeDefinition(self, ctx:Qasm2Parser.RangeDefinitionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumGateDefinition.
    def enterQuantumGateDefinition(self, ctx:Qasm2Parser.QuantumGateDefinitionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumGateDefinition.
    def exitQuantumGateDefinition(self, ctx:Qasm2Parser.QuantumGateDefinitionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumGateParameter.
    def enterQuantumGateParameter(self, ctx:Qasm2Parser.QuantumGateParameterContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumGateParameter.
    def exitQuantumGateParameter(self, ctx:Qasm2Parser.QuantumGateParameterContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumGateName.
    def enterQuantumGateName(self, ctx:Qasm2Parser.QuantumGateNameContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumGateName.
    def exitQuantumGateName(self, ctx:Qasm2Parser.QuantumGateNameContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumGateSignature.
    def enterQuantumGateSignature(self, ctx:Qasm2Parser.QuantumGateSignatureContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumGateSignature.
    def exitQuantumGateSignature(self, ctx:Qasm2Parser.QuantumGateSignatureContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumBlock.
    def enterQuantumBlock(self, ctx:Qasm2Parser.QuantumBlockContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumBlock.
    def exitQuantumBlock(self, ctx:Qasm2Parser.QuantumBlockContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumLoopBlock.
    def enterQuantumLoopBlock(self, ctx:Qasm2Parser.QuantumLoopBlockContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumLoopBlock.
    def exitQuantumLoopBlock(self, ctx:Qasm2Parser.QuantumLoopBlockContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumStatement.
    def enterQuantumStatement(self, ctx:Qasm2Parser.QuantumStatementContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumStatement.
    def exitQuantumStatement(self, ctx:Qasm2Parser.QuantumStatementContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumInstruction.
    def enterQuantumInstruction(self, ctx:Qasm2Parser.QuantumInstructionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumInstruction.
    def exitQuantumInstruction(self, ctx:Qasm2Parser.QuantumInstructionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumMeasurement.
    def enterQuantumMeasurement(self, ctx:Qasm2Parser.QuantumMeasurementContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumMeasurement.
    def exitQuantumMeasurement(self, ctx:Qasm2Parser.QuantumMeasurementContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumMeasurementAssignment.
    def enterQuantumMeasurementAssignment(self, ctx:Qasm2Parser.QuantumMeasurementAssignmentContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumMeasurementAssignment.
    def exitQuantumMeasurementAssignment(self, ctx:Qasm2Parser.QuantumMeasurementAssignmentContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumBarrier.
    def enterQuantumBarrier(self, ctx:Qasm2Parser.QuantumBarrierContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumBarrier.
    def exitQuantumBarrier(self, ctx:Qasm2Parser.QuantumBarrierContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#quantumGateCall.
    def enterQuantumGateCall(self, ctx:Qasm2Parser.QuantumGateCallContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#quantumGateCall.
    def exitQuantumGateCall(self, ctx:Qasm2Parser.QuantumGateCallContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#unaryOperator.
    def enterUnaryOperator(self, ctx:Qasm2Parser.UnaryOperatorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#unaryOperator.
    def exitUnaryOperator(self, ctx:Qasm2Parser.UnaryOperatorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#comparisonOperator.
    def enterComparisonOperator(self, ctx:Qasm2Parser.ComparisonOperatorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#comparisonOperator.
    def exitComparisonOperator(self, ctx:Qasm2Parser.ComparisonOperatorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#equalityOperator.
    def enterEqualityOperator(self, ctx:Qasm2Parser.EqualityOperatorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#equalityOperator.
    def exitEqualityOperator(self, ctx:Qasm2Parser.EqualityOperatorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#logicalOperator.
    def enterLogicalOperator(self, ctx:Qasm2Parser.LogicalOperatorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#logicalOperator.
    def exitLogicalOperator(self, ctx:Qasm2Parser.LogicalOperatorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#expressionStatement.
    def enterExpressionStatement(self, ctx:Qasm2Parser.ExpressionStatementContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#expressionStatement.
    def exitExpressionStatement(self, ctx:Qasm2Parser.ExpressionStatementContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#expression.
    def enterExpression(self, ctx:Qasm2Parser.ExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#expression.
    def exitExpression(self, ctx:Qasm2Parser.ExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#logicalAndExpression.
    def enterLogicalAndExpression(self, ctx:Qasm2Parser.LogicalAndExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#logicalAndExpression.
    def exitLogicalAndExpression(self, ctx:Qasm2Parser.LogicalAndExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#bitOrExpression.
    def enterBitOrExpression(self, ctx:Qasm2Parser.BitOrExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#bitOrExpression.
    def exitBitOrExpression(self, ctx:Qasm2Parser.BitOrExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#xOrExpression.
    def enterXOrExpression(self, ctx:Qasm2Parser.XOrExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#xOrExpression.
    def exitXOrExpression(self, ctx:Qasm2Parser.XOrExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#bitAndExpression.
    def enterBitAndExpression(self, ctx:Qasm2Parser.BitAndExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#bitAndExpression.
    def exitBitAndExpression(self, ctx:Qasm2Parser.BitAndExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#equalityExpression.
    def enterEqualityExpression(self, ctx:Qasm2Parser.EqualityExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#equalityExpression.
    def exitEqualityExpression(self, ctx:Qasm2Parser.EqualityExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#comparisonExpression.
    def enterComparisonExpression(self, ctx:Qasm2Parser.ComparisonExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#comparisonExpression.
    def exitComparisonExpression(self, ctx:Qasm2Parser.ComparisonExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#bitShiftExpression.
    def enterBitShiftExpression(self, ctx:Qasm2Parser.BitShiftExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#bitShiftExpression.
    def exitBitShiftExpression(self, ctx:Qasm2Parser.BitShiftExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#additiveExpression.
    def enterAdditiveExpression(self, ctx:Qasm2Parser.AdditiveExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#additiveExpression.
    def exitAdditiveExpression(self, ctx:Qasm2Parser.AdditiveExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#multiplicativeExpression.
    def enterMultiplicativeExpression(self, ctx:Qasm2Parser.MultiplicativeExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#multiplicativeExpression.
    def exitMultiplicativeExpression(self, ctx:Qasm2Parser.MultiplicativeExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#unaryExpression.
    def enterUnaryExpression(self, ctx:Qasm2Parser.UnaryExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#unaryExpression.
    def exitUnaryExpression(self, ctx:Qasm2Parser.UnaryExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#expressionTerminator.
    def enterExpressionTerminator(self, ctx:Qasm2Parser.ExpressionTerminatorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#expressionTerminator.
    def exitExpressionTerminator(self, ctx:Qasm2Parser.ExpressionTerminatorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#booleanLiteral.
    def enterBooleanLiteral(self, ctx:Qasm2Parser.BooleanLiteralContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#booleanLiteral.
    def exitBooleanLiteral(self, ctx:Qasm2Parser.BooleanLiteralContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#incrementor.
    def enterIncrementor(self, ctx:Qasm2Parser.IncrementorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#incrementor.
    def exitIncrementor(self, ctx:Qasm2Parser.IncrementorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#builtInCall.
    def enterBuiltInCall(self, ctx:Qasm2Parser.BuiltInCallContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#builtInCall.
    def exitBuiltInCall(self, ctx:Qasm2Parser.BuiltInCallContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#builtInMath.
    def enterBuiltInMath(self, ctx:Qasm2Parser.BuiltInMathContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#builtInMath.
    def exitBuiltInMath(self, ctx:Qasm2Parser.BuiltInMathContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#castOperator.
    def enterCastOperator(self, ctx:Qasm2Parser.CastOperatorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#castOperator.
    def exitCastOperator(self, ctx:Qasm2Parser.CastOperatorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#expressionList.
    def enterExpressionList(self, ctx:Qasm2Parser.ExpressionListContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#expressionList.
    def exitExpressionList(self, ctx:Qasm2Parser.ExpressionListContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#equalsExpression.
    def enterEqualsExpression(self, ctx:Qasm2Parser.EqualsExpressionContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#equalsExpression.
    def exitEqualsExpression(self, ctx:Qasm2Parser.EqualsExpressionContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#assignmentOperator.
    def enterAssignmentOperator(self, ctx:Qasm2Parser.AssignmentOperatorContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#assignmentOperator.
    def exitAssignmentOperator(self, ctx:Qasm2Parser.AssignmentOperatorContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#setDeclaration.
    def enterSetDeclaration(self, ctx:Qasm2Parser.SetDeclarationContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#setDeclaration.
    def exitSetDeclaration(self, ctx:Qasm2Parser.SetDeclarationContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#programBlock.
    def enterProgramBlock(self, ctx:Qasm2Parser.ProgramBlockContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#programBlock.
    def exitProgramBlock(self, ctx:Qasm2Parser.ProgramBlockContext):
        pass


    # Enter a parse tree produced by Qasm2Parser#branchingStatement.
    def enterBranchingStatement(self, ctx:Qasm2Parser.BranchingStatementContext):
        pass

    # Exit a parse tree produced by Qasm2Parser#branchingStatement.
    def exitBranchingStatement(self, ctx:Qasm2Parser.BranchingStatementContext):
        pass



del Qasm2Parser