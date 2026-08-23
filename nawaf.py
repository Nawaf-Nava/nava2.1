#data=input("entar the text :")
#key1 =int(input("enterthe key :"))
#key2=int(input("enterthe key :"))
#result=""

#for i in data:
 #   if i.isupper():
  #      a=chr((key1*(ord(i)-ord("A"))+key2)%26+ord("A"))
   # elif i.islower():
    #    a=chr((key1*(ord(i)-ord("a"))+key2)%26+ord("a"))
    #else:
    #    a=""
   # result+=a
#print(result)


b=int(input("enter the key :"))
a=26
while True:
    i=a//b
    r=a-(b*i)  
    a=b
    b=r
    if r==0:
        break
    a=b
    b=r
print(b)
data=input("entar the text :")
key1 =int(input("enterthe key :"))
key2=int(input("enterthe key :"))
result=""

for i in data:
    if i.isupper():
        a=chr((key1*(ord(i)-ord("A"))+key2)%26+ord("A"))
    elif i.islower():
        a=chr((key1*(ord(i)-ord("a"))+key2)%26+ord("a"))
    else:
        a=""
    result+=a
print(result)