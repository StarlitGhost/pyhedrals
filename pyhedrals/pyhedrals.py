# -*- coding: utf-8 -*-
import random
import operator
from builtins import range
import heapq
from collections import Counter as mset

from sly import Lexer, Parser


class UnknownCharacterException(Exception):
    pass


class SyntaxErrorException(Exception):
    pass


class InvalidOperandsException(Exception):
    pass


class Die(object):
    def __init__(self, numSides):
        self.numSides = numSides
        self.value = random.randint(1, self.numSides)
        self.exploded = False
        self.dropped = False

    def __str__(self):
        value = str(self.value)
        if self.exploded:
            value = '*{}*'.format(value)
        if self.dropped:
            value = '-{}-'.format(value)

        return value

    def __lt__(self, other):
        return self.value < other.value


class RollList(object):
    def __init__(self, numDice, numSides):
        self.numDice = numDice
        self.numSides = numSides
        self.rolls = [Die(numSides) for _ in range(0, numDice)]
        self.count = False

    def sum(self):
        return sum(self.getDieValue(r) for r in self.rolls if not r.dropped)

    def getDieValue(self, d):
        if self.count:
            return 1
        else:
            return d.value

    def sort(self, reverse=False):
        self.rolls = sorted(self.rolls, reverse=reverse)

    def __str__(self):
        return '{}d{}: {} ({})'.format(self.numDice, self.numSides,
                                        ','.join(str(die) for die in self.rolls),
                                        self.sum())


# Calculate the column position of the given token.
#     input is the input text string
#     token is a token instance
def _findColumn(text, token):
    if token is not None:
        last_cr = text.rfind('\n', 0, token.index)
        if last_cr < 0:
            last_cr = 0
        column = (token.index - last_cr) + 1
        return column
    else:
        return 'unknown'


class DiceLexer(Lexer):
    tokens = {NUMBER,
              PLUS, MINUS,
              TIMES, DIVIDE, MODULUS,
              EXPONENT,
              KEEPHIGHEST, KEEPLOWEST,
              DROPHIGHEST, DROPLOWEST,
              EXPLODE,
              REROLL,
              COUNT,
              SORT,
              DICE,
              LPAREN, RPAREN,
              COMMENT}
    ignore = ' \t'

    # Tokens
    PLUS = r'\+'
    MINUS = r'-'
    TIMES = r'\*'
    DIVIDE = r'/'
    MODULUS = r'%'
    EXPONENT = r'\^'
    KEEPHIGHEST = r'kh'
    KEEPLOWEST = r'kl'
    DROPHIGHEST = r'dh'
    DROPLOWEST = r'dl'
    EXPLODE = r'!([<>]=?)?'
    REROLL = r'ro?([<>]=?)?'
    COUNT = r'c([<>]=?)?'
    SORT = r's[ad]?'
    DICE = r'd'
    LPAREN = r'\('
    RPAREN = r'\)'

    @_(r'\d+')
    def NUMBER(self, t):
        try:
            if len(t.value) < 100:
                t.value = int(t.value)
            else:
                raise ValueError
        except ValueError:
            t.value = 0
        return t

    @_(r'\#.*')
    def COMMENT(self, t):
        t.value = str(t.value)[1:].strip()
        return t

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    def error(self, t):
        col = _findColumn(self.text, t)
        raise UnknownCharacterException("unknown character '{}' (col {})".format(t.value[0], col))


class DiceParser(Parser):
    def __init__(self, maxDice=10000, maxSides=10000, maxExponent=10000, maxMult=1000000):
        self.MAX_DICE = maxDice
        self.MAX_SIDES = maxSides
        self.MAX_EXPONENT = maxExponent
        self.MAX_MULT = maxMult

        self.rolls = []
        self.description = None

    tokens = DiceLexer.tokens

    # Parsing rules
    precedence = (('left', PLUS, MINUS),
                  ('left', TIMES, DIVIDE, MODULUS),
                  ('left', EXPONENT),
                  ('left', KEEPHIGHEST, KEEPLOWEST,
                           DROPHIGHEST, DROPLOWEST,
                           EXPLODE, REROLL, COUNT,
                           SORT),
                  ('left', DICE),
                  ('right', UMINUS),
                  ('right', UDICE))

    @_('expr PLUS expr',
       'expr MINUS expr',
       'expr TIMES expr',
       'expr DIVIDE expr',
       'expr MODULUS expr',
       'expr EXPONENT expr')
    def expr(self, p):
        op = p[1]
        left = self._sumDiceRolls(p.expr0)
        right = self._sumDiceRolls(p.expr1)

        if op == '+':
            return operator.add(left, right)
        elif op == '-':
            return operator.sub(left, right)
        elif op == '*':
            if (-self.MAX_MULT <= left <= self.MAX_MULT and
                    -self.MAX_MULT <= right <= self.MAX_MULT):
                return operator.mul(left, right)
            else:
                raise InvalidOperandsException(
                        'multiplication operands are larger than the maximum {}'
                        .format(self.MAX_MULT))
        elif op == '/':
            return operator.floordiv(left, right)
        elif op == '%':
            return operator.mod(left, right)
        elif op == '^':
            if (-self.MAX_EXPONENT <= left <= self.MAX_EXPONENT and
                    -self.MAX_EXPONENT <= right <= self.MAX_EXPONENT):
                return operator.pow(left, right)
            else:
                raise InvalidOperandsException(
                        'operand or exponent is larger than the maximum {}'
                        .format(self.MAX_EXPONENT))

    @_('MINUS expr %prec UMINUS')
    def expr(self, p):
        return operator.neg(self._sumDiceRolls(p.expr))

    @_('dice_expr')
    def expr(self, p):
        return p.dice_expr

    @_('expr DICE expr')
    def dice_expr(self, p):
        return self._rollDice(p.expr0, p.expr1)

    @_('DICE expr %prec UDICE')
    def dice_expr(self, p):
        return self._rollDice(1, p.expr)

    @_('')
    def empty(self, p):
        pass

    @_('dice_expr KEEPHIGHEST expr',
       'dice_expr KEEPLOWEST expr',
       'dice_expr DROPHIGHEST expr',
       'dice_expr DROPLOWEST expr',
       'dice_expr KEEPHIGHEST empty',
       'dice_expr KEEPLOWEST empty',
       'dice_expr DROPHIGHEST empty',
       'dice_expr DROPLOWEST empty')
    def dice_expr(self, p):
        rollList = p.dice_expr
        op = p[1]
        keepDrop = self._sumExpr(p) or 1

        # filter dice that have already been dropped
        validRolls = [r for r in rollList.rolls if not r.dropped]

        # if it's a drop op, invert the number into a keep count
        if op.startswith('d'):
            opType = 'drop'
            keepDrop = len(validRolls) - keepDrop
        else:
            opType = 'keep'

        if len(validRolls) < keepDrop:
            raise InvalidOperandsException(
                    'attempted to {} {} dice when only {} were rolled'
                    .format(opType, keepDrop, len(validRolls)))

        if op == 'kh' or op == 'dl':
            keptRolls = heapq.nlargest(keepDrop, validRolls)
        elif op == 'kl' or op == 'dh':
            keptRolls = heapq.nsmallest(keepDrop, validRolls)
        else:
            raise NotImplementedError(
                    "operator '{}' is not implemented (also, this should be impossible?)"
                    .format(op))

        # determine which rolls were dropped, and mark them as such
        dropped = list((mset(validRolls) - mset(keptRolls)).elements())
        for drop in dropped:
            index = rollList.rolls.index(drop)
            rollList.rolls[index].dropped = True

        return rollList

    @_('dice_expr EXPLODE expr',
       'dice_expr EXPLODE empty')
    def dice_expr(self, p):
        rollList = p.dice_expr
        op = p.EXPLODE

        threshold = self._sumExpr(p) or rollList.numSides
        comp = self._getComparisonOp('explode', op, p, threshold, rollList.numSides)

        debrisList = []
        def explode(die):
            die.exploded = True

            debris = Die(die.numSides)
            debrisList.append(debris)
            if comp(debris.value, threshold):
                explode(debris)

        for roll in rollList.rolls:
            if comp(roll.value, threshold):
                explode(roll)

        rollList.rolls.extend(debrisList)

        return rollList

    @_('dice_expr REROLL expr',
       'dice_expr REROLL empty')
    def dice_expr(self, p):
        rollList = p.dice_expr
        op = p.REROLL

        threshold = self._sumExpr(p) or 1
        comp = self._getComparisonOp('reroll', op, p, threshold, rollList.numSides)

        rerollList = []
        def reroll(die, recurse=True):
            die.dropped = True
            rerollDie = Die(die.numSides)
            rerollList.append(rerollDie)
            if recurse and comp(rerollDie.value, threshold):
                reroll(rerollDie)

        recurse = True
        if len(op) > 1 and op[1] == 'o':
            recurse = False

        for roll in rollList.rolls:
            if comp(roll.value, threshold):
                reroll(roll, recurse=recurse)

        rollList.rolls.extend(rerollList)

        return rollList

    @_('dice_expr COUNT expr',
       'dice_expr COUNT empty')
    def dice_expr(self, p):
        rollList = p.dice_expr
        op = p.COUNT

        threshold = self._sumExpr(p) or rollList.numSides
        comp = self._getComparisonOp('count', op, p, threshold, rollList.numSides)

        # filter dice that have already been dropped
        validRolls = [r for r in rollList.rolls if not r.dropped]
        for roll in validRolls:
            if not comp(roll.value, threshold):
                roll.dropped = True

        rollList.count = True
        return rollList

    def _sumExpr(self, p):
        if 'expr' in p._namemap:
            return self._sumDiceRolls(p.expr)

    def _getComparisonOp(self, opName, op, p, threshold, numSides):
        comp = operator.eq
        if op.endswith('<'):
            if threshold > numSides:
                raise InvalidOperandsException(
                        "{} threshold '<{}' is invalid with {} sided dice"
                        .format(opName, threshold, numSides))
            comp = operator.lt
        elif op.endswith('>'):
            if threshold < 1:
                raise InvalidOperandsException(
                        "{} threshold '>{}' is invalid"
                        .format(opName, threshold))
            comp = operator.gt
        elif op.endswith('<='):
            if threshold >= numSides:
                raise InvalidOperandsException(
                        "{} threshold '<={}' is invalid with {} sided dice"
                        .format(opName, threshold, numSides))
            comp = operator.le
        elif op.endswith('>='):
            if threshold <= 1:
                raise InvalidOperandsException(
                        "{} threshold '>={}' is invalid"
                        .format(opName, threshold))
            comp = operator.ge

        if comp == operator.eq:
            if not 1 <= threshold <= numSides:
                raise InvalidOperandsException(
                        "{} threshold '{}' is invalid with {} sided dice"
                        .format(opName, threshold, numSides))
        else:
            if 'expr' not in p._namemap:
                raise InvalidOperandsException(
                        "no parameter given to {} comparison"
                        .format(opName))

        return comp

    @_('dice_expr SORT')
    def dice_expr(self, p):
        rollList = p.dice_expr
        op = p.SORT

        reverse = False
        if op == 'sd':
            reverse = True

        rollList.sort(reverse)
        return rollList

    @_('LPAREN expr RPAREN')
    def expr(self, p):
        return p.expr

    @_('NUMBER')
    def expr(self, p):
        return p.NUMBER

    @_('expr COMMENT')
    def expr(self, p):
        self.description = p.COMMENT
        return p.expr

    def error(self, p):
        if p is None:
            raise SyntaxErrorException("syntax error at the end of the given expression")

        col = _findColumn(self._dice_expr, p)
        raise SyntaxErrorException(
                "syntax error at '{}' (col {})"
                .format(p.value, col))

    def _rollDice(self, numDice, numSides):
        numDice = self._sumDiceRolls(numDice)
        numSides = self._sumDiceRolls(numSides)

        if numDice > self.MAX_DICE:
            raise InvalidOperandsException(
                    'attempted to roll more than {} dice in a single d expression'
                    .format(self.MAX_DICE))
        if numSides > self.MAX_SIDES:
            raise InvalidOperandsException(
                    'attempted to roll a die with more than {} sides'
                    .format(self.MAX_SIDES))
        if numDice < 0:
            raise InvalidOperandsException(
                    'attempted to roll a negative number of dice')
        if numSides < 0:
            raise InvalidOperandsException(
                    'attempted to roll a die with a negative number of sides')
        if numSides < 1:
            raise InvalidOperandsException(
                    'attempted to roll a die with zero sides')

        return RollList(numDice, numSides)

    def _sumDiceRolls(self, rollList):
        """convert from dice roll structure to a single integer result"""
        if isinstance(rollList, RollList):
            self.rolls.append(rollList)
            return rollList.sum()
        else:
            return rollList


class DiceRoller(object):
    def __init__(self, maxDice=10000, maxSides=10000, maxExponent=10000, maxMult=1000000):
        self.lexer = DiceLexer()
        self.parser = DiceParser(maxDice, maxSides, maxExponent, maxMult)

    def reset(self):
        self.parser.rolls = []
        self.parser.description = None

    def parse(self, dice_expr):
        self.parser._dice_expr = dice_expr
        self.reset()

        result = self.parser.parse(self.lexer.tokenize(dice_expr))
        result = self.parser._sumDiceRolls(result)
        self.description = self.parser.description
        return result

    def getRollStrings(self):
        rollStrings = (str(roll) for roll in self.parser.rolls)
        return rollStrings


def main():
    import argparse
    argparser = argparse.ArgumentParser(description='An interpreter for dice expressions.')
    argparser.add_argument('-v', '--verbose', help='print all roll results', action='store_true')
    argparser.add_argument('diceexpr', help='the dice expression you want to execute', type=str)
    cmdArgs = argparser.parse_args()

    roller = DiceRoller()

    try:
        result = roller.parse(cmdArgs.diceexpr)
    except OverflowError:
        print('Error: result too large to calculate')
        return
    except (ZeroDivisionError,
            UnknownCharacterException,
            SyntaxErrorException,
            InvalidOperandsException,
            RecursionError,
            NotImplementedError) as e:
        print('Error: {}'.format(e))
        return

    if roller.description:
        result = '{} {}'.format(result, roller.description)

    if cmdArgs.verbose:
        rollStrings = roller.getRollStrings()
        rollString = ' | '.join(rollStrings)

        print('{}{}'.format('[{}] '.format(rollString) if rollString else '', result))
        return

    print(result)


if __name__ == '__main__':
    main()
