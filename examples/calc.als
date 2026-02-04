# Aerless Sample: Interactive Calculator
# ----------------------------------------

do "Aerless 電卓へようこそ！"

# 1. ユーザーから数値を入力してもらう
is num1 = get_num("1つ目の数字を入力してね: ")
is op   = get_op("記号を入力してね (+, -, *, /): ")
is num2 = get_num("2つ目の数字を入力してね: ")

# 2. 計算（条件分岐）
is result = 0

if op == "+" { result = num1 + num2 }
if op == "-" { result = num1 - num2 }
if op == "*" { result = num1 * num2 }
if op == "/" { 
    if num2 == 0 {
        do "エラー：0で割ることはできないよ！"
    } no {
        result = num1 / num2
    }
}

# 3. 結果を表示
do "--- 計算完了 ---"
do "{num1} {op} {num2} の答えは... {result} だよ！"