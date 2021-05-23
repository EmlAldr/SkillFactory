# Чтобы написать тест, мы должны определить функцию, имя которой начинается на test_  
# после этого мы используем ключевое слово assert, которое проверят, является ли истинным значение сразу за ним  
def test_something():  
    assert True  
      
def test_equal_string():  
    greetings = "Hello, " +  "world"  
    assert greetings == "Hello, world"  

def test_numbers():  
    total = 73 + 42  
    assert total == 115