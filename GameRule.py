import pygame

import Map1

from typing import Union
from pygame.math import Vector2

from Blocks import *
from GameState import *

stopStateStream = {}
pushStateStream = {}
youStateStream = {}
winStateStream = {}

class GameRuleObserver():
    def __init__(self, gameState):
        self._gameState = gameState

    def _is_inside_map(self, coordinate: Vector2) -> bool:
        """
        :param coordinate: 方块的坐标，Vector2类型
        :return: 返回方块是否在地图的范围内
        """
        if coordinate.x < 0 or coordinate.x >= WORLD_MAX_X*CELL_SIZE_X \
                or coordinate.y < 0 or coordinate.y >= WORLD_MAX_Y*CELL_SIZE_Y:
            return False
        else:
            return True

    def _is_exist(self, objectBlock: Union[GeneralBlock], direction: Vector2) -> Union[None, GeneralBlock]:
        """
        :param objectBlock: 某个特定的方块
        :param direction: 紧挨着object的方向
        :return: 返回object的direction方向是否有其他方块
                 除非返回None，否则返回一个特定block类型的数据，表示object在direction方向的方块信息
        """

        if direction != Vector2(0, 0):
            _newLocation = objectBlock.location + direction
            for unit in self._gameState.units:
                if unit.location == _newLocation and not unit.is_pass():
                    return unit
                else:
                    continue

    def _is_exist_line(self, objectBlock, direction) -> list:
        """
        :param objectBlock: 某个特定的方块
        :param direction: 紧挨着object的方向
        :return: 返回一个列表，元素依次表示方块沿direction方向的所有连续方块数据
        """

        nextBlock = self._is_exist(objectBlock, direction)
        lineBlockList = []
        while nextBlock is not None and not nextBlock.is_pass():
            lineBlockList.append(nextBlock)
            nextBlock = self._is_exist(nextBlock, direction)

        return lineBlockList

    def _observe(self, objectBlock: Union[GeneralBlock]) -> Union[list]:
        """
        :param objectBlock: 某个特定的方块
        :return: 按照"上下左右"的顺序返回被观察的方块四个方向上的方块数据，若某个方向上没有方块，则为None
        """

        blocksAroundList = []
        for direction in DIRECTION:
            blocksAroundList.append(self._is_exist(objectBlock, direction))

        return blocksAroundList

    def _is_collide(self, objectBlock, direction: Vector2) -> bool:
        """
        :param objectBlock: 某个特定的方块
        :param direction: 移动的方向
        :return: 返回True表示有碰撞
        """

        blockDirection = self._is_exist(objectBlock, direction)
        if blockDirection is not None and not blockDirection.is_move() and not blockDirection.is_pass():
            return True
        else:
            return False

    def _push(self, objectBlock, direction: Vector2):
        """
        当方块沿某个特定方向准备移动时，如果方向上有moveable=True的方块，则调用此函数进行移动
        :param objectBlock: 某个特定的方块
        :param direction: 移动方向
        :return: 无返回值，直接修改gameState中的方块位置
        """
        nextBlockLine = self._is_exist_line(objectBlock, direction)
        isPushSign = True

        for block in nextBlockLine:
            if not self._is_inside_map(block.location) or not block.is_move():
                isPushSign = False
                break

        if isPushSign:
            objectBlock.location += direction
            for block in nextBlockLine:
                block.location += direction

    def _move(self, objectBlock: Union[GeneralBlock], direction: Vector2):
        """
        :param objectBlock: 某个特定的方块
        :param direction: 移动的方向
        :return: 无返回值，直接修改gameState中的方块位置
        """
        if objectBlock.is_move() and objectBlock.is_control():
            _newLocation = objectBlock.location + direction

            if self._is_inside_map(_newLocation):
                nextBlock = self._is_exist(objectBlock, direction)
                if nextBlock is None or nextBlock.is_pass():
                    objectBlock.location = _newLocation
                    for blockNounName in winStateStream:  # 判断胜利条件
                        targetBlockName = "".join(blockNounName.split('Noun'))
                        if winStateStream[blockNounName]:
                            if type(nextBlock).__name__ == targetBlockName:
                                self._gameState.playerState = True
                else:
                    if not self._is_collide(objectBlock, direction):
                        self._push(objectBlock, direction)

    def _is_grammar_valid(self, objectBlock: Union[GeneralBlock]) -> list:
        """
        :param objectBlock: is方块（IsBlock）
        :return: 如果谓词分析后，上-is-下（或左-is-右）合法（Noun. + is + Verb.），则返回前后方块的信息，否则返回None
        """

        _isGrammarValid = [None] * 4
        _blocksAroundList = self._observe(objectBlock)
        for i in range(0, len(_blocksAroundList), 2):
            _firstBlock = _blocksAroundList[i]
            _secondBlock = _blocksAroundList[i+1]
            if _firstBlock is not None and _secondBlock is not None:
                if _firstBlock._text and _secondBlock._text:
                    if _firstBlock.word in NOUN_WORD_BANK and _secondBlock.word in VERB_WORD_BANK:
                        _isGrammarValid[i] = _firstBlock
                        _isGrammarValid[i+1] = _secondBlock

        return _isGrammarValid

    def _predicate_analyze(self, objectBlock: Union[GeneralBlock]) -> list:
        """
        谓词分析：对谓词"is"的四个方向进行检测，上-is-下（或左-is-右）可以继续进行谓词分析
        :return:
        """
        _isGrammarValid = [None] * 4
        _blocksAroundList = self._observe(objectBlock)
        for i in range(0, len(_blocksAroundList), 2):
            _firstBlock = _blocksAroundList[i]
            _secondBlock = _blocksAroundList[i + 1]
            if _firstBlock is not None and _secondBlock is not None:
                if _firstBlock._text and _secondBlock._text:
                    # text是否是语法方块
                    if _firstBlock.word in NOUN_WORD_BANK and _secondBlock.word == 'you':
                        _isGrammarValid[i] = _firstBlock
                        _isGrammarValid[i + 1] = _secondBlock
                    elif _firstBlock.word in NOUN_WORD_BANK and _secondBlock.word in NOUN_WORD_BANK:
                        _isGrammarValid[i] = _firstBlock
                        _isGrammarValid[i + 1] = _secondBlock

        return _isGrammarValid

    def is_directly_win(self, objectBlockList: list) -> bool:
        """
        仅一种胜利判定方式，即"xx is win", "xx is you"时xx的方块类型一致；
        另一种胜利判定方法，内置于move()函数中，接触时即做判定
        :param objectBlockList: 所有待判断的方块，一般是GameState().units
        :return: True表示获得胜利，游戏状态playerState变为False
        """

        _winSign = "win"
        _youSign = "you"
        _compareList = []

        for isBlock in objectBlockList:
            _isGrammarValid = self._is_grammar_valid(isBlock)
            for i in range(0, len(_isGrammarValid), 2):
                if _isGrammarValid[i] is None:
                    continue
                else:
                    if _winSign == _isGrammarValid[i+1].word or _youSign == _isGrammarValid[i+1].word:
                        _compareList.append(_isGrammarValid[i])

        if len(_compareList) == 2:
            return _compareList[0].word == _compareList[1].word
        else:
            return False

    def _update_state(self, stateStream: dict, objectBlockList: list, targetWord: str) -> None:
        """
        更新当前所有语法方块的状态，Python dict的key值表示方块名字，value值（bool）表示当前方块是否有某个状态
        :param stateStream: 状态流（dict）
        :param objectBlockList: 所有is方块构成的list
        :param targetWord: 待检测的目标动词
        :return: 无返回值，直接更新state stream
        """

        allGrammarBlocksList = []

        for isBlock in objectBlockList:
            _isGrammarValid = self._is_grammar_valid(isBlock)
            for i in range(0, len(_isGrammarValid), 2):
                if _isGrammarValid[i] is None:
                    continue
                else:
                    allGrammarBlocksList.append(type(_isGrammarValid[i]).__name__)
                    allGrammarBlocksList.append(_isGrammarValid[i+1])

        for i in range(0, len(allGrammarBlocksList), 2):  # 为stateStream初始化，默认都是False状态
            stateStream[allGrammarBlocksList[i]] = False

        for i in range(0, len(allGrammarBlocksList), 2):
            if allGrammarBlocksList[i+1].word == targetWord:  # 当匹配到状态时，调整为True
                stateStream[allGrammarBlocksList[i]] = True
                break
        for blockNounName in stateStream:
            if blockNounName not in allGrammarBlocksList:  # 当状态流里的状态不存在时，调整为False
                stateStream[blockNounName] = False

    def endow(self, objectBlockList: list) -> None:
        """
        根据语法规则判断是否需要赋予（修改）方块某些属性，若符合语法规则，则直接赋予属性
        :param objectBlockList: 所有is方块构成的list
        :return: 无返回值，直接在gameState中修改方块的状态
        """

        self._update_state(stopStateStream, objectBlockList, 'stop')
        self._update_state(pushStateStream, objectBlockList, 'push')
        self._update_state(youStateStream, objectBlockList, 'you')
        self._update_state(winStateStream, objectBlockList, 'win')

        for blockNounName in stopStateStream:
            targetBlockName = "".join(blockNounName.split('Noun'))
            if youStateStream[blockNounName]:  # 更新具有you状态的方块属性
                for unit in self._gameState.units:
                    if type(unit).__name__ == targetBlockName:
                        unit._controllable = True
                        unit._moveable = True
            else:
                for unit in self._gameState.units:
                    if type(unit).__name__ == targetBlockName:
                        unit._controllable = False

            if not stopStateStream[blockNounName] and not pushStateStream[blockNounName]:  # 更新具有stop和push状态的方块属性
                for unit in self._gameState.units:
                    if type(unit).__name__ == targetBlockName and not unit.is_control():
                        unit._passable = True
                        unit._moveable = False
            elif stopStateStream[blockNounName] and not pushStateStream[blockNounName]:
                for unit in self._gameState.units:
                    if type(unit).__name__ == targetBlockName and not unit.is_control():
                        unit._passable = False
                        unit._moveable = False
            elif not stopStateStream[blockNounName] and pushStateStream[blockNounName]:
                for unit in self._gameState.units:
                    if type(unit).__name__ == targetBlockName and not unit.is_control():
                        unit._passable = False
                        unit._moveable = True
            else:
                for unit in self._gameState.units:
                    if type(unit).__name__ == targetBlockName and not unit.is_control():
                        unit._passable = False
                        unit._moveable = False

    def transform(self, objectBlock: Union[GeneralBlock]):
        blockAround = self._predicate_analyze(objectBlock)
        #print(blockAround)
        for i in range(0, len(blockAround), 2):
            if blockAround[i] is not None:
                # 当语法成立时，移除所有方块可被操作属性，如果后面有subject is you语句成立，再赋予controllable
                if blockAround[i + 1].word == 'you':
                    for unit_j in range(len(self._gameState.units)):
                        self._gameState.units[unit_j]._controllable = False
                    # 当宾语为you时，给主语赋予controllable is True
                    nounBlockTypeName = type(blockAround[i]).__name__
                    targetBlockTypeName = "".join(nounBlockTypeName.split("Noun"))
                    for unit_j in range(len(self._gameState.units)):
                        if type(self._gameState.units[unit_j]).__name__ == targetBlockTypeName:
                            self._gameState.units[unit_j]._controllable = True
                else:
                    # 当语法成立且宾语不为you时，定为方块转换关系，分别得到主语宾语的类名，
                    nounBlockTypeName = type(blockAround[i]).__name__
                    targetBlockTypeName = "".join(nounBlockTypeName.split("Noun"))
                    nounBlockTypeName1 = type(blockAround[i + 1]).__name__
                    targetBlockTypeName1 = "".join(nounBlockTypeName1.split("Noun"))
                    # 遍历所有与主语类名相同的方块，将主语类名变为宾语类名，主语属性变为宾语属性

                    for j in self._gameState.units:
                        if type(j).__name__ == targetBlockTypeName1:
                            temp=j
                    for x in range(len(self._gameState.units)):
                        #print(x)
                        # print(Map1.units[1].location)
                        #print(targetBlockTypeName)
                        if type(self._gameState.units[x]).__name__ == targetBlockTypeName:
                            self._gameState.units[x]._id = j._id
                            self._gameState.units[x]._text = j._text
                            self._gameState.units[x]._passable = j._passable
                            self._gameState.units[x]._moveable = j._moveable
                            self._gameState.units[x]._controllable = j._controllable
                            self._gameState.units[x].location = j.location
                            self._gameState.units[x].texture = pygame.image.load(j.a)
                            self._gameState.units[x].rect = j.rect
                            # print("*",Map1.units[1].location)
                            # #print(self._gameState.units[x])
                            # templocation = self._gameState.units[x].location
                            # print("**",Map1.units[1].location)
                            #
                            # #print(templocation)
                            # #print(self._gameState.units[x])
                            # print(x)
                            # self._gameState.units[x] = j
                            # print("***",Map1.units[1].location,Map1.units[2].location)
                            # a=x
                            # self._gameState.units[a].location = templocation
                            #
                            # #print(Map1.units[2].texture)
                            # print(Map1.units[1].location,Map1.units[2].location,Map1.units[4].location,templocation)
                            #print(self._gameState.units[j].a,self._gameState.units[j].location)