import uiautomator2 as u2

d = u2.connect()
d.app_start("com.sankuai.sailor.afooddelivery")
print(d(textContains="Previsão").get_text())